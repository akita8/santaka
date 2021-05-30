from typing import List
from random import randint

from aiohttp import ClientSession
from fastapi import status, HTTPException
from sqlalchemy.sql import select
from passlib.context import CryptContext

from santaka.db import database, accounts, owners, users
from santaka.models import User, NewStockTransaction, TransactionType

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_FIELD_PRICE = "regularMarketPrice"
YAHOO_FIELD_MARKET = "fullExchangeName"
YAHOO_FIELD_CURRENCY = "currency"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


async def get_owner(user_id: int, owner_id: int):
    # this query also checks that the owner exists
    # and that it's linked to one of the users accounts
    query = (
        select(
            [
                accounts.c.account_id,
                accounts.c.bank,
                accounts.c.account_number,
                owners.c.owner_id,
                owners.c.fullname,
            ]
        )
        .select_from(
            accounts.join(owners, accounts.c.account_id == owners.c.account_id),
        )
        .where(accounts.c.user_id == user_id)
        .where(owners.c.owner_id == owner_id)
    )
    record = await database.fetch_one(query)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Owner {owner_id} doesn't exist",
        )
    return record


def create_random_id(length: int = 15):
    return randint(10 ** (length - 1), (10 ** (length) - 1))


def verify_password(plain_password, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(username: str, password: str):
    hashed_password = pwd_context.hash(password)
    query = users.insert().values(
        user_id=create_random_id(), username=username, password=hashed_password
    )
    user_id = await database.execute(query)
    print(f"created user {username} with {user_id} id")


async def get_user(username: str):
    query = users.select().where(users.c.username == username)
    record = await database.fetch_one(query)
    if record is None:
        return None, None
    return User(username=username, user_id=record.user_id), record.password


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
