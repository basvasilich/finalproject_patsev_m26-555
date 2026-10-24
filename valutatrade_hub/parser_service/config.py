import os
from dataclasses import dataclass, field

from valutatrade_hub.infra.settings import SettingsLoader


@dataclass
class ParserConfig:
    """Источники, валюты и ограничения HTTP-запросов."""

    BASE_CURRENCY: str = field(
        default_factory=lambda: SettingsLoader().get("BASE_CURRENCY")
    )
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
    )
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_URL: str = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"
    REQUEST_TIMEOUT: float = 10
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", ""), repr=False
    )
