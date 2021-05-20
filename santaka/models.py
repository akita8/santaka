from decimal import Decimal
from typing import List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, conlist


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    user_id: int


class NewAccount(BaseModel):
    owners: conlist(str, min_items=1)
    bank: str
    account_number: str


class Account(NewAccount):
    account_id: int


class Accounts(BaseModel):
    accounts: List[Account]


class NewStock(BaseModel):
    isin: str
    market: str
    symbol: str
    currency: str


class Stock(NewStock):
    stock_id: int
    last_price: Decimal


class TransactionType(str, Enum):
    buy = "buy"
    sell = "sell"


class NewStockTransaction(BaseModel):
    account_id: int
    price: Decimal
    quantity: int
    tax: Decimal = 0
    commission: Decimal = 0
    date: datetime
    transaction_type: TransactionType


class StockTransaction(NewStockTransaction):
    stock_transaction_id: int
