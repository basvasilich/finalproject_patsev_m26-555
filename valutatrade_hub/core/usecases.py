from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.infra.storage import JsonRepository

from .currencies import get_currency
from .exceptions import StorageError
from .models import Portfolio, User
from .utils import empty_rates, get_rate, validate_number


class TradingService:
    """Регистрация, сессия и операции с портфелем."""

    def __init__(self):
        settings = SettingsLoader()
        self.users = JsonRepository(settings.data_path("USERS_FILE"))
        self.portfolios = JsonRepository(settings.data_path("PORTFOLIOS_FILE"))
        self.rates = JsonRepository(settings.data_path("RATES_FILE"), empty_rates)
        self.current_user = None

    def register(self, username, password):
        """Зарегистрировать пользователя с пустым портфелем."""
        users = self.users.load()
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        if any(item["username"] == username.strip() for item in users):
            raise ValueError(f"Пользователь '{username.strip()}' уже существует")
        user_id = max((item["user_id"] for item in users), default=0) + 1
        user = User(user_id, username, password)
        portfolios = self.portfolios.load()
        self.users.save([*users, user.to_dict()])
        try:
            self.portfolios.save([*portfolios, Portfolio(user).to_dict()])
        except StorageError:
            self.users.save(users)
            raise
        return user.get_user_info()

    def login(self, username, password):
        """Проверить пароль и открыть сессию текущего процесса."""
        self.current_user = None
        for item in self.users.load():
            if item["username"] == username.strip():
                user = User.from_dict(item)
                if not user.verify_password(password):
                    raise ValueError("Неверный пароль")
                self.current_user = user
                return user.get_user_info()
        raise ValueError(f"Пользователь '{username}' не найден")

    def _load_portfolio(self):
        if self.current_user is None:
            raise ValueError("Сначала выполните login")
        portfolios = self.portfolios.load()
        for index, item in enumerate(portfolios):
            if item["user_id"] == self.current_user.user_id:
                return portfolios, index, Portfolio.from_dict(item, self.current_user)
        raise StorageError("Портфель пользователя не найден")

    def show_portfolio(self, base="USD"):
        """Вернуть балансы, их стоимость и итог в базовой валюте."""
        _, _, portfolio = self._load_portfolio()
        base = get_currency(base).code
        cache = self.rates.load()

        def rate_provider(source, target):
            return get_rate(source, target, cache)

        rows = []
        for code, wallet in sorted(portfolio.wallets.items()):
            value = (
                wallet.balance * rate_provider(code, base)["rate"]
                if wallet.balance
                else 0
            )
            rows.append((code, wallet.balance, value))
        return {
            "base": base,
            "rows": rows,
            "total": portfolio.get_total_value(base, rate_provider),
        }

    @log_action
    def buy(self, currency_code, amount):
        """Купить валюту за USD с атомарным сохранением двух балансов."""
        return self._trade(currency_code, amount, buying=True)

    @log_action
    def sell(self, currency_code, amount):
        """Продать валюту за USD с атомарным сохранением двух балансов."""
        return self._trade(currency_code, amount, buying=False)

    def _trade(self, currency_code, amount, buying):
        portfolios, index, portfolio = self._load_portfolio()
        code = get_currency(currency_code).code
        amount = validate_number(amount)
        rate = get_rate(code, "USD")["rate"]
        cost = validate_number(amount * rate)
        usd = portfolio.add_currency("USD")
        wallet = portfolio.add_currency(code) if buying else portfolio.get_wallet(code)
        before = {key: item.balance for key, item in portfolio.wallets.items()}
        if buying:
            usd.withdraw(cost)
            wallet.deposit(amount)
        else:
            wallet.withdraw(amount)
            usd.deposit(cost)
        portfolios[index] = portfolio.to_dict()
        self.portfolios.save(portfolios)
        return {
            "currency": code,
            "amount": amount,
            "rate": rate,
            "cost": cost,
            "before": before,
            "after": {key: item.balance for key, item in portfolio.wallets.items()},
        }

    def get_rate(self, from_code, to_code):
        """Получить курс из локального кэша."""
        return get_rate(from_code, to_code)

    def show_rates(self, currency=None, top=None, base="USD"):
        """Отфильтровать и отсортировать свежие курсы по убыванию."""
        base = get_currency(base).code
        currency = get_currency(currency).code if currency else None
        if top is not None and top <= 0:
            raise ValueError("top должен быть положительным целым числом")
        cache = self.rates.load()
        codes = {pair.split("_")[0] for pair in cache.get("pairs", {})}
        if currency:
            codes = {currency}
        if not codes:
            raise ValueError("Кэш пуст; сначала выполните update-rates")
        rows = [
            {"currency": code, "base": base, **get_rate(code, base, cache)}
            for code in codes
        ]
        return sorted(rows, key=lambda row: (-row["rate"], row["currency"]))[:top]
