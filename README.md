# ValutaTrade Hub

Учебный валютный кошелёк с покупкой и продажей за USD. Нужны Python 3.12+ и uv.

## Запуск

```sh
git clone https://github.com/basvasilich/finalproject_patsev_m26-555.git
cd finalproject_patsev_m26-555
uv sync
uv run valutatrade
```

В приложении выполните `register --username alice --password 1234`, затем `exit`.
Для тестовой покупки задайте баланс в `data/local/portfolios.json`:

```json
[{"user_id": 1, "wallets": {"USD": {"balance": 10000.0}}}]
```

Снова запустите `uv run valutatrade`. Вход действует до выхода,
балансы сохраняются между запусками.

```text
login --username alice --password 1234
update-rates
show-rates --top 2
buy --currency BTC --amount 0.01
sell --currency BTC --amount 0.005
show-portfolio --base USD
get-rate --from BTC --to USD
exit
```

Для фиатных курсов ExchangeRate-API перед запуском задайте ключ в окружении.
Не сохраняйте его в Git. Без ключа работает только источник CoinGecko.

```sh
read -rs -p 'ExchangeRate API key: ' EXCHANGERATE_API_KEY
export EXCHANGERATE_API_KEY
```

## Устройство

`core` — модели и операции, `infra` — настройки и JSON,
`parser_service` — получение курсов, `cli` — команды.
Настройки — `[tool.valutatrade]` в `pyproject.toml`.

`update-rates` получает курсы CoinGecko и ExchangeRate-API независимо.
Для выбора API: `--source coingecko` или `--source exchangerate`.
`rates.json` хранит `pairs` с `rate`, `updated_at`, `source` и общий `last_refresh`.
Пара FROM_TO — единицы TO за единицу FROM. TTL — 300 секунд,
после истечения нужен `update-rates`. История — `exchange_rates.json`.

Рабочие JSON — `data/local/`, логи — `logs/actions.log`; они исключены из Git.
`data/*.json` — пустые шаблоны.

Проверка: `uv run ruff check .` и `uv run ruff format --check .`.
[Демо](docs/demo.cast): `asciinema play docs/demo.cast`.
