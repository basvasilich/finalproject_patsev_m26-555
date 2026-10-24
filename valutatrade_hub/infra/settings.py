import tomllib
from pathlib import Path


class SettingsLoader:
    """Единая кэшированная конфигурация приложения."""

    _instance = None
    DEFAULTS = {
        "DATA_DIR": "data/local",
        "LOG_DIR": "logs",
        "USERS_FILE": "users.json",
        "PORTFOLIOS_FILE": "portfolios.json",
        "RATES_FILE": "rates.json",
        "HISTORY_FILE": "exchange_rates.json",
        "RATES_TTL_SECONDS": 300,
        "BASE_CURRENCY": "USD",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s %(levelname)s %(message)s",
        "LOG_MAX_BYTES": 1048576,
        "LOG_BACKUP_COUNT": 3,
    }

    def __new__(cls):
        # __new__ сохраняет один экземпляр независимо от места вызова.
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._values = cls.DEFAULTS.copy()
            path = Path("pyproject.toml")
            if path.exists():
                with path.open("rb") as stream:
                    config = tomllib.load(stream)
                instance._values.update(config.get("tool", {}).get("valutatrade", {}))
            cls._instance = instance
        return cls._instance

    def get(self, key, default=None):
        """Получить значение настройки."""
        return self._values.get(key, default)

    def data_path(self, key):
        """Получить путь к файлу данных."""
        return Path(self.get("DATA_DIR")) / self.get(key)
