import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from .currencies import get_currency
from .exceptions import InsufficientFundsError
from .utils import get_rate, parse_time, validate_number


class User:
    """Пользователь с солёным хешем пароля."""

    def __init__(self, user_id, username, password):
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        self._user_id = user_id
        self._username = username.strip()
        self._registration_date = datetime.now(UTC)
        self.change_password(password)

    @property
    def user_id(self):
        """Идентификатор пользователя."""
        return self._user_id

    @property
    def username(self):
        """Имя пользователя."""
        return self._username

    @property
    def registration_date(self):
        """Дата регистрации."""
        return self._registration_date

    def get_user_info(self):
        """Вернуть данные без пароля, соли и хеша."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password):
        """Сменить пароль, обновив соль и SHA-256."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов")
        self._salt = secrets.token_hex(16)
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()

    def verify_password(self, password):
        """Сравнить хеши паролей без раннего выхода."""
        if not isinstance(password, str):
            return False
        digest = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hmac.compare_digest(digest, self._hashed_password)

    def to_dict(self):
        """Сериализовать пользователя для JSON."""
        return {
            **self.get_user_info(),
            "hashed_password": self._hashed_password,
            "salt": self._salt,
        }

    @classmethod
    def from_dict(cls, data):
        """Восстановить пользователя без повторного хеширования."""
        user = cls(data["user_id"], data["username"], secrets.token_hex(16))
        user._hashed_password = data["hashed_password"]
        user._salt = data["salt"]
        user._registration_date = parse_time(data["registration_date"])
        return user


class Wallet:
    """Баланс одной валюты без овердрафта."""

    def __init__(self, currency_code, balance=0.0):
        self.currency_code = get_currency(currency_code).code
        self.balance = balance

    @property
    def balance(self):
        """Текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value):
        self._balance = validate_number(value, allow_zero=True)

    def deposit(self, amount):
        """Пополнить кошелёк положительной суммой."""
        self.balance += validate_number(amount)

    def withdraw(self, amount):
        """Снять сумму при достаточном остатке."""
        amount = validate_number(amount)
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)
        self.balance -= amount

    def get_balance_info(self):
        """Краткая строка баланса."""
        return f"{self.balance:.4f} {self.currency_code}"


class Portfolio:
    """Уникальные валютные кошельки пользователя."""

    def __init__(self, user):
        self._user = user
        self._wallets = {}

    @property
    def user(self):
        """Владелец портфеля, только для чтения."""
        return self._user

    @property
    def wallets(self):
        """Копия словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, code):
        """Создать отсутствующий кошелёк."""
        code = get_currency(code).code
        if code not in self._wallets:
            self._wallets[code] = Wallet(code)
        return self._wallets[code]

    def get_wallet(self, code):
        """Получить существующий кошелёк."""
        code = get_currency(code).code
        if code not in self._wallets:
            raise ValueError(f"Кошелёк {code} не найден")
        return self._wallets[code]

    def get_total_value(self, base_currency="USD", rate_provider=get_rate):
        """Оценить портфель по свежим курсам."""
        base_currency = get_currency(base_currency).code
        return sum(
            wallet.balance * rate_provider(code, base_currency)["rate"]
            for code, wallet in self._wallets.items()
            if wallet.balance
        )

    def to_dict(self):
        """Сериализовать кошельки и связь с пользователем."""
        return {
            "user_id": self.user.user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data, user):
        """Восстановить портфель из JSON."""
        if data["user_id"] != user.user_id:
            raise ValueError("Владелец портфеля не совпадает")
        portfolio = cls(user)
        for code, item in data["wallets"].items():
            portfolio.add_currency(code).balance = item["balance"]
        return portfolio
