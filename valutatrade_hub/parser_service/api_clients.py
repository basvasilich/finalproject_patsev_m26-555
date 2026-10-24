import time
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import validate_number

from .config import ParserConfig


class BaseApiClient(ABC):
    """HTTP-клиент с единым форматом курсов FROM_TO."""

    source = "API"

    def __init__(self, config=None):
        self.config = config or ParserConfig()
        self.metadata = {}

    def _request(self, url, params=None):
        started = time.monotonic()
        try:
            response = requests.get(
                url, params=params, timeout=self.config.REQUEST_TIMEOUT
            )
            if response.status_code == 401:
                raise ApiRequestError(f"{self.source}: HTTP 401, проверьте ключ")
            if response.status_code == 429:
                raise ApiRequestError(f"{self.source}: HTTP 429, лимит запросов")
            if response.status_code != 200:
                raise ApiRequestError(f"{self.source}: HTTP {response.status_code}")
            data = response.json()
        except ApiRequestError:
            raise
        except requests.exceptions.JSONDecodeError:
            raise ApiRequestError(f"{self.source}: некорректный JSON") from None
        except requests.RequestException as error:
            raise ApiRequestError(f"{self.source}: {type(error).__name__}") from None
        except ValueError:
            raise ApiRequestError(f"{self.source}: некорректный JSON") from None
        if not isinstance(data, dict):
            raise ApiRequestError(f"{self.source}: ожидался JSON-объект")
        self.metadata = {
            "request_ms": round((time.monotonic() - started) * 1000),
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
        }
        return data

    @abstractmethod
    def fetch_rates(self):
        """Получить словарь положительных курсов FROM_TO."""


class CoinGeckoClient(BaseApiClient):
    """Курсы криптовалют через CoinGecko Simple Price."""

    source = "CoinGecko"

    def fetch_rates(self):
        """Преобразовать API ID в валютные коды."""
        base = self.config.BASE_CURRENCY
        data = self._request(
            self.config.COINGECKO_URL,
            {
                "ids": ",".join(self.config.CRYPTO_ID_MAP.values()),
                "vs_currencies": base.lower(),
            },
        )
        try:
            return {
                f"{code}_{base}": validate_number(data[coin_id][base.lower()])
                for code, coin_id in self.config.CRYPTO_ID_MAP.items()
            }
        except (KeyError, ValueError, TypeError):
            raise ApiRequestError("CoinGecko: некорректные курсы") from None


class ExchangeRateApiClient(BaseApiClient):
    """Фиатные курсы через ExchangeRate-API v6."""

    source = "ExchangeRate-API"

    def fetch_rates(self):
        """Инвертировать BASE→валюта в валютa→BASE."""
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("задайте EXCHANGERATE_API_KEY в окружении")
        base = self.config.BASE_CURRENCY
        url = self.config.EXCHANGERATE_URL.format(
            key=self.config.EXCHANGERATE_API_KEY, base=base
        )
        data = self._request(url)
        if data.get("result") != "success" or data.get("base_code") != base:
            raise ApiRequestError("ExchangeRate-API: ответ неуспешен или неверная база")
        try:
            rates = data["conversion_rates"]
            return {
                f"{code}_{base}": validate_number(1 / validate_number(rates[code]))
                for code in self.config.FIAT_CURRENCIES
                if code != base
            }
        except (KeyError, ValueError, TypeError):
            raise ApiRequestError("ExchangeRate-API: некорректные курсы") from None
