import argparse
import shlex
import sys

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CURRENCIES
from valutatrade_hub.core.exceptions import ApiRequestError, CurrencyNotFoundError
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.updater import RatesUpdater


def build_parser():
    """Создать парсер восьми команд."""
    parser = argparse.ArgumentParser(prog="valutatrade")
    parser.add_argument("--verbose", action="store_true", help="Подробный журнал")
    commands = parser.add_subparsers(dest="command")
    for name in ("register", "login"):
        command = commands.add_parser(name)
        command.add_argument("--username", required=True)
        command.add_argument("--password", required=True)
    command = commands.add_parser("show-portfolio")
    command.add_argument("--base", default="USD")
    for name in ("buy", "sell"):
        command = commands.add_parser(name)
        command.add_argument("--currency", required=True)
        command.add_argument("--amount", required=True, type=float)
    command = commands.add_parser("get-rate")
    command.add_argument("--from", dest="from_code", required=True)
    command.add_argument("--to", dest="to_code", required=True)
    command = commands.add_parser("update-rates")
    command.add_argument("--source", choices=("coingecko", "exchangerate"))
    command = commands.add_parser("show-rates")
    command.add_argument("--currency")
    command.add_argument("--top", type=int)
    command.add_argument("--base", default="USD")
    return parser


def execute(args, service):
    """Вызвать usecase и вывести результат."""
    match args.command:
        case "register" | "login":
            user = getattr(service, args.command)(args.username, args.password)
            prefix = (
                "Зарегистрирован" if args.command == "register" else "Вход выполнен"
            )
            print(f"{prefix}: {user['username']} (id={user['user_id']})")
        case "show-portfolio":
            result = service.show_portfolio(args.base)
            if not result["rows"]:
                print("Портфель пуст")
                return
            table = PrettyTable(["Валюта", "Баланс", f"Стоимость, {result['base']}"])
            for code, balance, value in result["rows"]:
                table.add_row([code, f"{balance:.4f}", f"{value:.2f}"])
            print(table)
            print(f"Итого: {result['total']:.2f} {result['base']}")
        case "buy" | "sell":
            result = getattr(service, args.command)(args.currency, args.amount)
            verb = "Куплено" if args.command == "buy" else "Продано"
            print(f"{verb}: {result['amount']:g} {result['currency']}")
            print(f"Курс: {result['rate']:g} USD; стоимость: {result['cost']:.2f} USD")
            for code, balance in result["after"].items():
                print(f"{code}: {result['before'][code]:g} → {balance:g}")
        case "get-rate":
            result = service.get_rate(args.from_code, args.to_code)
            print(
                f"{args.from_code.upper()} → {args.to_code.upper()}: "
                f"{result['rate']:.8g} ({result['updated_at']})"
            )
        case "update-rates":
            clients = None
            if args.source:
                client = (
                    CoinGeckoClient
                    if args.source == "coingecko"
                    else ExchangeRateApiClient
                )
                clients = [client()]
            result = RatesUpdater(clients).run_update()
            print(
                f"Обновлено курсов: {result['count']}; "
                f"last_refresh: {result['last_refresh']}"
            )
            for error in result["errors"]:
                print(f"Частичный сбой: {error}. Подробнее в logs/actions.log")
        case "show-rates":
            rows = service.show_rates(args.currency, args.top, args.base)
            table = PrettyTable(["Пара", "Курс", "Обновлено"])
            for row in rows:
                table.add_row(
                    [
                        f"{row['currency']}/{row['base']}",
                        f"{row['rate']:.8g}",
                        row["updated_at"],
                    ]
                )
            print(table)


def dispatch(arguments, parser, service):
    """Обработать одну команду без traceback для пользовательских ошибок."""
    try:
        args = parser.parse_args(arguments)
        if args.command is None:
            parser.print_help()
        else:
            execute(args, service)
        return 0
    except SystemExit as error:
        return error.code
    except CurrencyNotFoundError as error:
        print(f"{error}. Доступны: {', '.join(CURRENCIES)}")
    except ApiRequestError as error:
        print(f"{error}. Проверьте сеть/ключ или повторите позже")
    except ValueError as error:
        print(error)
    except (KeyError, TypeError, AttributeError):
        print("Некорректная структура локальных данных")
    return 1


def main():
    """Запустить отдельную команду или интерактивную сессию."""
    parser = build_parser()
    try:
        setup_logging("--verbose" in sys.argv[1:])
        service = TradingService()
        if any(value != "--verbose" for value in sys.argv[1:]):
            return dispatch(sys.argv[1:], parser, service)
        print("ValutaTrade Hub. help — команды, exit — выход")
        while True:
            try:
                line = input("valuta> ").strip()
                if line == "exit":
                    return 0
                if line == "help":
                    parser.print_help()
                elif line:
                    dispatch(shlex.split(line), parser, service)
            except ValueError as error:
                print(error)
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
    except (OSError, ValueError) as error:
        print(f"Не удалось запустить приложение: {error}")
        return 1
