from decimal import Decimal
from typing import List
from enum import Enum
from os import environ
from logging import getLogger
from datetime import datetime, timedelta

from aiohttp import ClientSession
from fastapi import status, HTTPException
from pytz import timezone, utc
from sqlalchemy import asc
from sqlalchemy.sql import select

from santaka.stock.models import (
    TransactionType,
    NewStockTransaction,
)
from santaka.account import Bank
from santaka.db import database, stocks, currency

logger = getLogger(__name__)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_FIELD_PRICE = "regularMarketPrice"
YAHOO_FIELD_MARKET = "fullExchangeName"
YAHOO_FIELD_CURRENCY = "currency"
YAHOO_UPDATE_COOLDOWN = environ.get("YAHOO_UPDATE_COOLDOWN", 60 * 5)
YAHOO_UPDATE_DELTA = 60 * 60


class YahooMarket(str, Enum):
    ITALY = "Milan"
    UK = "LSE"
    EU = "EXTRA"
    USA = "NasdaqGS"
    CANADA = "Toronto"


ITALIAN_TAX = Decimal("0.26")
DOUBLE_TAX_MARKETS = {
    YahooMarket.EU.value: Decimal("0.26"),
    YahooMarket.USA.value: Decimal("0.15"),
    YahooMarket.CANADA.value: Decimal("0.15"),
}

MARKET_TIMEZONES = {
    YahooMarket.USA.value: timezone("America/New_York"),
    YahooMarket.UK.value: timezone("Europe/London"),
    YahooMarket.EU.value: timezone("Europe/Berlin"),
    YahooMarket.ITALY.value: timezone("Europe/Rome"),
    YahooMarket.CANADA.value: timezone("America/Toronto"),
}
TRADING_START = 8
TRADING_END = 18
DEFAULT_TRADING_TIMEZONE = MARKET_TIMEZONES[YahooMarket.ITALY.value]


class YahooError(Exception):
    pass


async def get_yahoo_quote(symbols: List[str]):
    async with ClientSession() as session:
        async with session.get(
            YAHOO_QUOTE_URL,
            params={
                "symbols": ",".join(symbols),
                "fields": ",".join(
                    [YAHOO_FIELD_PRICE, YAHOO_FIELD_CURRENCY, YAHOO_FIELD_MARKET]
                ),
            },
        ) as resp:
            if resp.status != 200:
                raise YahooError(f"yahoo answered with {resp.status} status")
            response = await resp.json()
    quotes = {}
    for quote in response["quoteResponse"]["result"]:
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
            detail="First transaction mast be a buy",
        )
    if records and transaction.transaction_type == TransactionType.sell:
        quantity = 0
        for record in records:
            if record.transaction_type == TransactionType.sell.value:
                quantity -= record.quantity
            else:
                quantity += record.quantity
        if quantity < transaction.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot sell more than {quantity} stocks",
            )


def calculate_commission(
    bank: str, market: str, price: Decimal, quantity: int
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
        if market == YahooMarket.USA.value:
            return Decimal("12.95")
        if market == YahooMarket.UK.value:
            return Decimal("14.95") + invested * Decimal("0.005")
        # TODO add "buy condition" where the commission is fixed 14.95£
    if bank == Bank.BG_SAXO.value:
        bg_saxo_commission = invested * Decimal("0.0017")
        if market == YahooMarket.ITALY.value:
            if bg_saxo_commission <= Decimal("2.5"):
                return Decimal("2.5")
            if bg_saxo_commission >= Decimal("17.5"):
                return Decimal("17.5")
            return bg_saxo_commission
        if market == YahooMarket.USA.value:
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
    return Decimal("0")


def calculate_sell_tax(
    market: str, fiscal_price: Decimal, last_price: Decimal, quantity: int
) -> Decimal:
    amount = last_price * quantity - fiscal_price * quantity  # forse le commissioni?
    if amount > 0:
        if market == YahooMarket.ITALY.value:
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
                stocks.join(currency, stocks.c.currency_id == currency.c.currency_id)
            )
            .where(
                stocks.c.market.in_(active_markets),
            )
            .where(stocks.c.last_update < one_hour_before)
            .order_by(asc(stocks.c.last_update))
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
                    f"yahoo returned less quotes than requsted: {quotes.keys()}"
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
