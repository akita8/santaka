from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from os import environ
from logging import getLogger
from datetime import datetime, timedelta

from aiohttp import ClientSession
from fastapi import status, HTTPException
from pytz import timezone, utc
from sqlalchemy import asc
from sqlalchemy.sql import select

from santaka.analytics import (
    calculate_fiscal_price,
    calculate_profit_and_loss,
    calculate_totals,
)
from santaka.stock.models import (
    AlertFields,
    NewStockTransaction,
    TradedStock,
    StockAlert,
    TransactionType,
    Transaction,
)
from santaka.account import Bank
from santaka.db import (
    database,
    stocks,
    currency,
    stock_transactions,
    accounts,
    owners,
    stock_alerts,
)

logger = getLogger(__name__)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_FIELD_PRICE = "regularMarketPrice"
YAHOO_FIELD_FINANCIAL_CURRENCY = "financialCurrency"
YAHOO_FIELD_MARKET = "fullExchangeName"
YAHOO_FIELD_CURRENCY = "currency"
YAHOO_FIELD_NAME = "shortName"
YAHOO_UPDATE_COOLDOWN = environ.get("YAHOO_UPDATE_COOLDOWN", 60 * 5)
YAHOO_UPDATE_DELTA = 60 * 60


class YahooMarket(str, Enum):
    ITALY = "Milan"
    UK = "LSE"
    EU = "XETRA"
    USA_NASDAQ = "NasdaqGS"
    USA_NYSE = "NYSE"
    CANADA = "Toronto"


ITALIAN_TAX = Decimal("0.26")
DOUBLE_TAX_MARKETS = {
    YahooMarket.EU.value: Decimal("0.26"),
    YahooMarket.USA_NASDAQ.value: Decimal("0.15"),
    YahooMarket.USA_NYSE.value: Decimal("0.15"),
    YahooMarket.CANADA.value: Decimal("0.15"),
}

MARKET_TIMEZONES = {
    YahooMarket.USA_NASDAQ.value: timezone("America/New_York"),
    YahooMarket.USA_NYSE.value: timezone("America/New_York"),
    YahooMarket.UK.value: timezone("Europe/London"),
    YahooMarket.EU.value: timezone("Europe/Berlin"),
    YahooMarket.ITALY.value: timezone("Europe/Rome"),
    YahooMarket.CANADA.value: timezone("America/Toronto"),
}
TRADING_START = 8
TRADING_END = 18
DEFAULT_TRADING_TIMEZONE = MARKET_TIMEZONES[YahooMarket.ITALY.value]

TransactionRecords = Tuple[
    int,  # stock_id 0
    str,  # iso_currency 1
    Decimal,  # last_rate 2
    str,  # symbol 3
    Decimal,  # last_price 4
    str,  # market 5
    str,  # transaction_type 6
    int,  # quantity 7
    Decimal,  # price 8
    Decimal,  # commission 9
    datetime,  # date 10
    Decimal,  # tax 11
    str,  # bank 12
    int,  # owner_id 13
    str,  # financial_currency 14
    str,  # short_name 15
]


class YahooError(Exception):
    pass


async def get_yahoo_quote(symbols: List[str]) -> Dict[str, Any]:
    async with ClientSession() as session:
        async with session.get(
            YAHOO_QUOTE_URL,
            params={
                "symbols": ",".join(symbols),
                "fields": ",".join(
                    [
                        YAHOO_FIELD_PRICE,
                        YAHOO_FIELD_CURRENCY,
                        YAHOO_FIELD_MARKET,
                        YAHOO_FIELD_NAME,
                        YAHOO_FIELD_FINANCIAL_CURRENCY,
                    ]
                ),
            },
        ) as resp:
            if resp.status != 200:
                raise YahooError(f"yahoo answered with {resp.status} status")
            response = await resp.json()
    quotes = {}
    for quote in response["quoteResponse"]["result"]:
        if quote[YAHOO_FIELD_MARKET] == YahooMarket.UK.value:
            quote[YAHOO_FIELD_PRICE] = quote[YAHOO_FIELD_PRICE] / 100
        quotes[quote["symbol"]] = quote
    return quotes


async def call_yahoo_from_view(symbol: str):
    try:
        quotes = await get_yahoo_quote([symbol])
    except YahooError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Call to provider unsuccessful",
        )
    if symbol not in quotes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol} doesn't exist",
        )
    return quotes[symbol]


def validate_stock_transaction(records, transaction: NewStockTransaction):
    if not records and transaction.transaction_type == TransactionType.sell:
        # fab:  >> if not << this sentence is the right way to identify an empty list
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="First transaction must be a buy",
        )
    quantity = 0
    for record in records:
        if (
            record.stock_id == transaction.stock_id
            and record.price == transaction.price
            and record.quantity == transaction.quantity
            and record.tax == transaction.tax
            and record.commission == transaction.commission
            and record.transaction_type == transaction.transaction_type
            and record.date.year == transaction.date.year
            and record.date.month == transaction.date.month
            and record.date.day == transaction.date.day
            and record.transaction_note == transaction.transaction_note
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You cannot duplicate a transaction",
            )

        if record.transaction_type == TransactionType.sell.value:
            quantity -= record.quantity
        else:
            quantity += record.quantity
    if (
        transaction.transaction_type == TransactionType.sell
        and quantity < transaction.quantity
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot sell more than {quantity} stocks",
        )


def calculate_commission(
    bank: str, market: str, price: Decimal, quantity: int, financial_currency: str
) -> Decimal:
    invested = price * quantity
    if bank == Bank.FINECOBANK.value:
        fineco_commission = invested * Decimal("0.0019")
        if market == YahooMarket.ITALY.value or market == YahooMarket.EU.value:
            if fineco_commission <= Decimal("2.95"):
                return Decimal("2.95")
            if fineco_commission > Decimal("19"):
                return Decimal("19")
            return fineco_commission
        if (
            market == YahooMarket.USA_NYSE.value
            or market == YahooMarket.USA_NASDAQ.value
        ):
            return Decimal("12.95")
        if market == YahooMarket.UK.value:
            return Decimal("14.95") + invested * Decimal("0.005")
    if bank == Bank.BG_SAXO.value:
        bg_saxo_commission = invested * Decimal("0.0017")
        if market == YahooMarket.ITALY.value:
            if bg_saxo_commission <= Decimal("2.5"):
                return Decimal("2.5")
            if bg_saxo_commission >= Decimal("17.5"):
                return Decimal("17.5")
            return bg_saxo_commission
        if (
            market == YahooMarket.USA_NYSE.value
            or market == YahooMarket.USA_NASDAQ.value
        ):
            return Decimal("11")
        if market == YahooMarket.EU.value:
            return Decimal("11")
        if market == YahooMarket.UK.value:
            return Decimal("11") + invested * Decimal("0.005")
        if market == YahooMarket.CANADA.value:
            return Decimal("11") + invested * Decimal("0.005")
    if bank == Bank.BANCA_GENERALI.value and market == YahooMarket.ITALY.value:
        banca_generali_commission = invested * Decimal("0.0015")
        if banca_generali_commission <= Decimal("8.00"):
            return Decimal("8.00")
        if banca_generali_commission > Decimal("20"):
            return Decimal("20")
        return banca_generali_commission
    if bank == Bank.CHE_BANCA.value:
        che_banca_commission = invested * Decimal("0.0018")
        if market == YahooMarket.ITALY.value and financial_currency == "USD":
            return Decimal("12")
        if market == YahooMarket.ITALY.value:
            if che_banca_commission <= Decimal("6"):
                return Decimal("6")
            if che_banca_commission >= Decimal("25"):
                return Decimal("25")
            return che_banca_commission
        if market == YahooMarket.EU.value:
            if che_banca_commission <= Decimal("12"):
                return Decimal("12")
            if che_banca_commission >= Decimal("35"):
                return Decimal("35")
            return che_banca_commission
        if (
            market == YahooMarket.USA_NYSE.value
            or market == YahooMarket.USA_NASDAQ.value
        ):
            return Decimal("12")
    return Decimal("0")


def calculate_sell_tax(
    market: str, fiscal_price: Decimal, last_price: Decimal, quantity: int
) -> Decimal:
    amount = last_price * quantity - fiscal_price * quantity
    if amount > 0:
        if market == YahooMarket.ITALY.value:
            return amount * ITALIAN_TAX
        if market == YahooMarket.UK.value:
            return amount * ITALIAN_TAX
        if market in DOUBLE_TAX_MARKETS:
            tax = amount * DOUBLE_TAX_MARKETS[market]
            foreign_taxed_amount = amount - tax
            return foreign_taxed_amount * ITALIAN_TAX + tax

    return Decimal("0")


def get_active_markets(dt: datetime) -> List[str]:
    markets = []
    utc_now = utc.localize(dt)
    for market, zone in MARKET_TIMEZONES.items():
        timezoned_now = utc_now.astimezone(zone)
        if timezoned_now.weekday() in (5, 6):
            continue
        start_of_day = timezoned_now.replace(
            hour=TRADING_START, minute=0, second=0, microsecond=0
        )
        end_of_day = timezoned_now.replace(
            hour=TRADING_END, minute=0, second=0, microsecond=0
        )
        if timezoned_now > start_of_day and timezoned_now < end_of_day:
            markets.append(market)
    return markets


@database.transaction()
async def update_stocks():
    now = datetime.utcnow()
    one_hour_before = now + timedelta(seconds=YAHOO_UPDATE_DELTA)
    active_markets = get_active_markets(now)
    if active_markets:
        query = (
            select(
                [
                    stocks.c.symbol,
                    currency.c.symbol,
                    stocks.c.stock_id,
                    currency.c.currency_id,
                ]
            )
            .select_from(
                stocks.join(
                    currency, stocks.c.currency_id == currency.c.currency_id
                ).join(
                    stock_transactions, stocks.stock_id == stock_transactions.stock_id
                )
            )
            .where(
                stocks.c.market.in_(active_markets),
            )
            .where(stocks.c.last_update < one_hour_before)
            .order_by(asc(stocks.c.last_update))
            .distinct()
        )
        oldest_stock = await database.fetch_one(query)
        if oldest_stock:
            (
                stock_symbol,
                currency_symbol,
                stock_id,
                currency_id,
            ) = oldest_stock
            logger.info(
                "trying to update %s stock and %s currency", stock_id, currency_id
            )
            quotes = await get_yahoo_quote([stock_symbol, currency_symbol])
            if len(quotes) != 2:
                raise YahooError(
                    f"yahoo returned less quotes than requested: {quotes.keys()}"
                )
            query = (
                stocks.update()
                .values(
                    last_price=quotes[stock_symbol][YAHOO_FIELD_PRICE],
                    last_update=now,
                )
                .where(stocks.c.stock_id == stock_id)
            )
            await database.execute(query)
            query = (
                currency.update()
                .values(
                    last_rate=quotes[currency_symbol][YAHOO_FIELD_PRICE],
                    last_update=now,
                )
                .where(currency.c.currency_id == currency_id)
            )
            await database.execute(query)


@database.transaction()
async def update_currency():
    now = datetime.utcnow()
    one_hour_before = now + timedelta(seconds=YAHOO_UPDATE_DELTA)
    timezoned_now = now.astimezone(DEFAULT_TRADING_TIMEZONE)
    if timezoned_now.weekday() in (5, 6):
        return
    query = (
        currency.select()
        .where(
            currency.c.last_update < one_hour_before,
        )
        .order_by(asc(currency.c.last_update))
    )
    oldest_currency = await database.fetch_one(query)
    if oldest_currency:
        logger.info("trying to update %d currency", oldest_currency.currency_id)
        quotes = await get_yahoo_quote([oldest_currency.symbol])
        if currency.symbol not in quotes:
            raise YahooError(
                "yahoo failed to return the quote for %s", oldest_currency.symbol
            )
        query = (
            currency.update()
            .values(
                last_rate=quotes[currency.symbol][YAHOO_FIELD_PRICE],
                last_update=now,
            )
            .where(currency.c.currency_id == oldest_currency.currency_id)
        )
        await database.execute(query)


def prepare_traded_stocks(
    transaction_records: List[TransactionRecords],
) -> List[TradedStock]:
    traded_stocks = []
    previous_stock_id = None
    if transaction_records:
        previous_stock_id = transaction_records[0][0]
        transaction_records.append(
            [None]
        )  # this triggers the addition of the last stock
    current_transactions = []
    current_quantity = 0
    for i, record in enumerate(transaction_records):
        if previous_stock_id != record[0]:
            previous_stock_id = record[0]
            previous_record = transaction_records[i - 1]
            fiscal_price = 0
            profit_and_loss = 0
            invested = 0
            current_ctv = 0
            current_ctv_converted = 0
            if current_quantity > 0:  # FIXME use fiscal price split aware quantity
                fiscal_price = calculate_fiscal_price(current_transactions)
                commission = calculate_commission(
                    previous_record[12],
                    previous_record[5],
                    previous_record[4],
                    current_quantity,
                    previous_record[14],
                )
                sell_tax = calculate_sell_tax(
                    previous_record[5],
                    fiscal_price,
                    previous_record[4],
                    current_quantity,  # total qty of all transactions of one stock_id
                )
                profit_and_loss = calculate_profit_and_loss(
                    fiscal_price,
                    previous_record[4],  # last_price
                    sell_tax,
                    commission,  # sell_commission
                    current_quantity,
                )
                invested, current_ctv, current_ctv_converted = calculate_totals(
                    fiscal_price,
                    previous_record[4],  # last_price
                    current_quantity,
                    previous_record[2],  # last_rate)
                )
            traded_stocks.append(
                {
                    "stock_id": previous_record[0],
                    "currency": previous_record[1],
                    "symbol": previous_record[3],
                    "last_price": previous_record[4],
                    "market": previous_record[5],
                    "fiscal_price": fiscal_price,
                    "profit_and_loss": profit_and_loss,
                    "owner_id": previous_record[13],
                    "current_quantity": current_quantity,
                    "invested": invested,
                    "current_ctv": current_ctv,
                    "current_ctv_converted": current_ctv_converted,
                    "short_name": previous_record[15],
                }
            )
            # here we are resetting the tax and qty to zero
            # and transactions to empty list for the next group of transactions
            current_quantity = 0
            current_transactions = []
        if i != len(transaction_records) - 1:
            current_transactions.append(
                Transaction(
                    transaction_type=record[6],
                    quantity=record[7],
                    price=record[8],
                    commission=record[9],
                    date=record[10],
                )
            )
            if record[6] == TransactionType.buy.value:
                current_quantity += record[7]  # buy type will add qty
            else:
                current_quantity -= record[7]  # sell type will reduce qty
    return traded_stocks


async def get_transaction_records(
    owner_ids: List[int],
    stock_id: Optional[int] = None,
) -> List[TransactionRecords]:
    query = (
        select(
            [
                stocks.c.stock_id,
                currency.c.iso_currency,
                currency.c.last_rate,
                stocks.c.symbol,
                stocks.c.last_price,
                stocks.c.market,
                stock_transactions.c.transaction_type,
                stock_transactions.c.quantity,
                stock_transactions.c.price,
                stock_transactions.c.commission,
                stock_transactions.c.date,
                stock_transactions.c.tax,
                accounts.c.bank,
                owners.c.owner_id,
                stocks.c.financial_currency,
                stocks.c.short_name,
            ]
        )
        .select_from(
            stock_transactions.join(
                stocks, stock_transactions.c.stock_id == stocks.c.stock_id
            )
            .join(currency, currency.c.currency_id == stocks.c.currency_id)
            .join(owners, stock_transactions.c.owner_id == owners.c.owner_id)
            .join(accounts, owners.c.account_id == accounts.c.account_id)
        )
        .where(stock_transactions.c.owner_id.in_(owner_ids))
        .order_by(
            stocks.c.stock_id,
            stock_transactions.c.date,
        )
    )
    if stock_id is not None:
        query = query.where(stocks.c.stock_id == stock_id)
    return await database.fetch_all(query)


def check_dividend_date(dividend_date: datetime) -> bool:
    return dividend_date <= datetime.utcnow()


def check_lower_limit_price(last_price: Decimal, lower_limit: Decimal) -> bool:
    return last_price <= lower_limit


def check_upper_limit_price(last_price: Decimal, upper_limit: Decimal) -> bool:
    return last_price > upper_limit


def check_fiscal_price_lower_than(last_price: Decimal, fiscal_price: Decimal) -> bool:
    return last_price < fiscal_price


def check_fiscal_price_greater_than(last_price: Decimal, fiscal_price: Decimal) -> bool:
    return last_price > fiscal_price


def check_profit_and_loss_upper_limit(limit: Decimal, profit_and_loss: Decimal) -> bool:
    return profit_and_loss > limit


def check_profit_and_loss_lower_limit(limit: Decimal, profit_and_loss: Decimal) -> bool:
    return profit_and_loss < limit


async def check_stock_alerts(
    stock_id: Optional[int] = None,
    owner_id: Optional[int] = None,
) -> List[StockAlert]:
    query = stock_alerts.select()
    if stock_id is not None:
        query = query.where(stock_alerts.c.stock_id == stock_id)
    if owner_id is not None:
        query = query.where(stock_alerts.c.owner_id == owner_id)
    alert_records = await database.fetch_all(query)
    indexed_alerts = {}
    owner_ids = []
    for alert in alert_records:
        indexed_alerts[(alert.owner_id, alert.stock_id)] = alert
        owner_ids.append(alert.owner_id)
    transaction_records = await get_transaction_records(owner_ids, stock_id)
    traded_stocks = prepare_traded_stocks(transaction_records)
    alerts = []
    for stock in traded_stocks:
        alert = indexed_alerts.get((stock["owner_id"], stock["stock_id"]))
        if alert is None:
            continue
        triggered_fields = []
        if alert.lower_limit_price is not None and check_lower_limit_price(
            stock["last_price"], alert.lower_limit_price
        ):
            triggered_fields.append(AlertFields.LOWER_LIMIT_PRICE)
        if alert.upper_limit_price is not None and check_upper_limit_price(
            stock["last_price"], alert.upper_limit_price
        ):
            triggered_fields.append(AlertFields.UPPER_LIMIT_PRICE)
        if alert.dividend_date is not None and check_dividend_date(alert.dividend_date):
            triggered_fields.append(AlertFields.DIVIDEND_DATE)
        if alert.fiscal_price_lower_than and check_fiscal_price_lower_than(
            stock["last_price"], stock["fiscal_price"]
        ):
            triggered_fields.append(AlertFields.FISCAL_PRICE_LOWER_THAN)
        if alert.fiscal_price_greater_than and check_fiscal_price_greater_than(
            stock["last_price"], stock["fiscal_price"]
        ):
            triggered_fields.append(AlertFields.FISCAL_PRICE_GREATER_THAN)
        if (
            alert.profit_and_loss_lower_limit is not None
            and check_profit_and_loss_lower_limit(
                alert.profit_and_loss_lower_limit, stock["profit_and_loss"]
            )
        ):
            triggered_fields.append(AlertFields.PROFIT_AND_LOSS_LOWER_LIMIT)
        if (
            alert.profit_and_loss_upper_limit is not None
            and check_profit_and_loss_upper_limit(
                alert.profit_and_loss_upper_limit, stock["profit_and_loss"]
            )
        ):
            triggered_fields.append(AlertFields.PROFIT_AND_LOSS_UPPER_LIMIT)
        alerts.append(
            {
                "stock_id": alert.stock_id,
                "owner_id": alert.owner_id,
                "lower_limit_price": alert.lower_limit_price,
                "upper_limit_price": alert.upper_limit_price,
                "dividend_date": alert.dividend_date,
                "fiscal_price_lower_than": alert.fiscal_price_lower_than,
                "fiscal_price_greater_than": alert.fiscal_price_greater_than,
                "profit_and_loss_lower_limit": alert.profit_and_loss_lower_limit,
                "profit_and_loss_upper_limit": alert.profit_and_loss_upper_limit,
                "stock_alert_id": alert.stock_alert_id,
                "triggered_fields": triggered_fields,
            }
        )
    return alerts
