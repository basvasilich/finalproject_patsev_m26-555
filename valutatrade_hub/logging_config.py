import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .infra.settings import SettingsLoader


class ISOFormatter(logging.Formatter):
    """Время лога в ISO UTC."""

    def formatTime(self, record, datefmt=None):
        """Преобразовать время записи в ISO."""
        return datetime.fromtimestamp(record.created, UTC).isoformat()


def setup_logging(verbose=False):
    """Настроить общий журнал с ротацией по размеру."""
    settings = SettingsLoader()
    logger = logging.getLogger("valutatrade")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    directory = Path(settings.get("LOG_DIR"))
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "actions.log",
        maxBytes=settings.get("LOG_MAX_BYTES"),
        backupCount=settings.get("LOG_BACKUP_COUNT"),
        encoding="utf-8",
    )
    handler.setFormatter(ISOFormatter(settings.get("LOG_FORMAT")))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else settings.get("LOG_LEVEL"))
    logger.propagate = False
