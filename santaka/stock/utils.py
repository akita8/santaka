from decimal import Decimal
from typing import List
from enum import Enum

from aiohttp import ClientSession
from fastapi import status, HTTPException

from santaka.stock.models import (
    TransactionType,
    NewStockTransaction,
)
from santaka.account import Bank

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_FIELD_PRICE = "regularMarketPrice"
YAHOO_FIELD_MARKET = "fullExchangeName"
YAHOO_FIELD_CURRENCY = "currency"


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
                raise YahooError()
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
