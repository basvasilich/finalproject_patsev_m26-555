import json
import logging
from functools import wraps


def log_action(func):
    """Логировать сделку и пробрасывать её исключения."""

    @wraps(func)
    def wrapper(self, currency_code, amount):
        user = self.current_user
        context = {
            "action": func.__name__.upper(),
            "user_id": user.user_id if user else None,
            "currency_code": currency_code,
            "amount": amount,
            "base": "USD",
        }
        logger = logging.getLogger("valutatrade")
        try:
            result = func(self, currency_code, amount)
        except Exception as error:
            logger.info(
                "%s",
                json.dumps(
                    {
                        **context,
                        "result": "ERROR",
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    },
                    ensure_ascii=False,
                ),
            )
            raise
        logger.info(
            "%s",
            json.dumps(
                {**context, "rate": result["rate"], "result": "OK"},
                ensure_ascii=False,
            ),
        )
        logger.debug("Баланс до → после: %s → %s", result["before"], result["after"])
        return result

    return wrapper
