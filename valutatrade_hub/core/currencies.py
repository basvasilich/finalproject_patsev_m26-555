import re
from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Валюта с именем и кодом."""

    def __init__(self, name, code):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не должно быть пустым")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2,5}", code):
            raise ValueError("Код валюты: 2–5 заглавных латинских букв")
        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self):
        """Вернуть описание валюты."""


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(self, name, code, issuing_country):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self):
        """Вернуть описание с эмитентом."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(self, name, code, algorithm, market_cap):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self):
        """Вернуть описание с алгоритмом и капитализацией."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("Pound Sterling", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof-of-Stake", 0),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof-of-Stake", 0),
}


def get_currency(code):
    """Найти валюту по коду без учёта регистра."""
    if not isinstance(code, str) or code.strip().upper() not in CURRENCIES:
        raise CurrencyNotFoundError(code)
    return CURRENCIES[code.strip().upper()]
