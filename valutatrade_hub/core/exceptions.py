class InsufficientFundsError(ValueError):
    """Недостаточный баланс кошелька."""

    def __init__(self, available, required, code):
        super().__init__(
            f"Недостаточно средств: доступно {available:g} {code}, "
            f"требуется {required:g} {code}"
        )


class CurrencyNotFoundError(ValueError):
    """Неизвестный код валюты."""

    def __init__(self, code):
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValueError):
    """Недоступный источник или курс."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class StorageError(ValueError):
    """Ошибка чтения или сохранения JSON."""
