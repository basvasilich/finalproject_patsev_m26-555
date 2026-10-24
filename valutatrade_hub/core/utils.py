import math
from datetime import UTC, datetime

from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.infra.storage import JsonRepository

from .currencies import get_currency
from .exceptions import ApiRequestError


def utc_now():
    """Текущее время в ISO UTC."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value):
    """Прочитать ISO-время; даты без зоны считать UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def validate_number(value, allow_zero=False):
    """Проверить конечную неотрицательную или положительную сумму."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (value == 0 and not allow_zero)
    ):
        raise ValueError("Сумма должна быть положительным конечным числом")
    return float(value)


def empty_rates():
    """Пустой срез курсов."""
    return {"pairs": {}, "last_refresh": None}


def get_rate(from_code, to_code, cache=None):
    """Получить свежий прямой, обратный или кросс-курс через USD."""
    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code
    if from_code == to_code:
        return {"rate": 1.0, "updated_at": utc_now()}
    settings = SettingsLoader()
    if cache is None:
        cache = JsonRepository(settings.data_path("RATES_FILE"), empty_rates).load()
    pairs = cache.get("pairs", {})
    if not isinstance(pairs, dict):
        raise ApiRequestError("неверный формат кэша; выполните update-rates")

    def lookup(source, target):
        for key, inverse in (
            (f"{source}_{target}", False),
            (f"{target}_{source}", True),
        ):
            item = pairs.get(key)
            if not isinstance(item, dict):
                continue
            try:
                rate = validate_number(item["rate"])
                updated = parse_time(item["updated_at"])
                age = (datetime.now(UTC) - updated).total_seconds()
                if 0 <= age <= settings.get("RATES_TTL_SECONDS"):
                    return {
                        "rate": validate_number(1 / rate if inverse else rate),
                        "updated_at": updated.isoformat().replace("+00:00", "Z"),
                    }
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
        raise ApiRequestError(
            f"курс {source}/{target} отсутствует или устарел; выполните update-rates"
        )

    try:
        return lookup(from_code, to_code)
    except ApiRequestError:
        if "USD" in (from_code, to_code):
            raise
    first = lookup(from_code, "USD")
    second = lookup(to_code, "USD")
    try:
        rate = validate_number(first["rate"] / second["rate"])
    except ValueError:
        raise ApiRequestError(
            "некорректный кросс-курс; выполните update-rates"
        ) from None
    return {
        "rate": rate,
        "updated_at": min(first["updated_at"], second["updated_at"]),
    }
