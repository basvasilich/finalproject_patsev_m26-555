from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.utils import empty_rates, parse_time, validate_number
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.infra.storage import JsonRepository


class RatesStorage:
    """Последний срез и история измерений без дубликатов."""

    def __init__(self):
        settings = SettingsLoader()
        self.cache = JsonRepository(settings.data_path("RATES_FILE"), empty_rates)
        self.history = JsonRepository(settings.data_path("HISTORY_FILE"))

    def save(self, measurements, refreshed_at):
        """Сохранить историю и обновить только более свежие пары."""
        cache = self.cache.load()
        history = self.history.load()
        existing = {item["id"] for item in history}
        pairs = cache.setdefault("pairs", {})
        for item in measurements:
            source = get_currency(item["from_currency"]).code
            target = get_currency(item["to_currency"]).code
            rate = validate_number(item["rate"])
            timestamp = parse_time(item["timestamp"])
            key = f"{source}_{target}"
            old = pairs.get(key)
            if old is None or timestamp > parse_time(old["updated_at"]):
                pairs[key] = {
                    "rate": rate,
                    "updated_at": item["timestamp"],
                    "source": item["source"],
                }
            if item["id"] not in existing:
                history.append(item)
                existing.add(item["id"])
        previous = cache.get("last_refresh")
        if previous is None or parse_time(refreshed_at) > parse_time(previous):
            cache["last_refresh"] = refreshed_at
        self.history.save(history)
        self.cache.save(cache)
