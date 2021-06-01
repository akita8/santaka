from decimal import Decimal
from typing import List

from aiohttp import ClientSession
from fastapi import status, HTTPException

from santaka.stock.models import (
    TransactionType,
    NewStockTransaction,
)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_FIELD_PRICE = "regularMarketPrice"
YAHOO_FIELD_MARKET = "fullExchangeName"
YAHOO_FIELD_CURRENCY = "currency"


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


# TODO implement these 3 functions and related tests in tests/test_stock.py

def calculate_commission(
    bank: str, market: str, price: Decimal, quantity: int
) -> Decimal:
    pass


def calculate_stamp_europe(market: str) -> Decimal:
    pass


def calculate_stamp_uk(price: Decimal, quantity: int) -> Decimal:
    pass
