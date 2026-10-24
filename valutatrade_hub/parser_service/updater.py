import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import utc_now

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RatesStorage


class RatesUpdater:
    """Обновление кэша с независимым опросом источников."""

    def __init__(self, clients=None, storage=None):
        self.clients = (
            clients
            if clients is not None
            else [CoinGeckoClient(), ExchangeRateApiClient()]
        )
        self.storage = storage or RatesStorage()

    def run_update(self):
        """Сохранить доступные курсы даже при отказе одного источника."""
        logger = logging.getLogger("valutatrade")
        logger.info("UPDATE start")
        measurements = []
        errors = []
        for client in self.clients:
            try:
                rates = client.fetch_rates()
                if not rates:
                    raise ApiRequestError(f"{client.source}: пустой ответ")
            except ApiRequestError as error:
                logger.warning("UPDATE source=%s result=ERROR %s", client.source, error)
                errors.append(error.reason)
                continue
            timestamp = utc_now()
            for pair, rate in rates.items():
                source, target = pair.split("_")
                metadata = dict(client.metadata)
                if isinstance(client, CoinGeckoClient):
                    metadata["raw_id"] = client.config.CRYPTO_ID_MAP[source]
                measurements.append(
                    {
                        "id": f"{pair}_{timestamp}",
                        "from_currency": source,
                        "to_currency": target,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": client.source,
                        "meta": metadata,
                    }
                )
            logger.info(
                "UPDATE source=%s result=OK count=%s", client.source, len(rates)
            )
        if not measurements:
            raise ApiRequestError("; ".join(errors))
        refreshed = utc_now()
        self.storage.save(measurements, refreshed)
        logger.info(
            "UPDATE result=OK count=%s last_refresh=%s", len(measurements), refreshed
        )
        return {"count": len(measurements), "last_refresh": refreshed, "errors": errors}
