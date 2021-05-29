from decimal import Decimal
from typing import List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, conlist, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    user_id: int


class Owner(BaseModel):
    name: str
    owner_id: int


class NewAccount(BaseModel):
    owners: conlist(str, min_items=1)  # fab: checks that exists at least one owner
    bank: str
    account_number: str


class Account(NewAccount):
    account_id: int
    owners: List[Owner]


class Accounts(BaseModel):
    accounts: List[Account]


class NewStock(BaseModel):
    isin: str
    symbol: str


class Stock(NewStock):
    stock_id: int


class TransactionType(str, Enum):
    buy = "buy"
    sell = "sell"


class Transaction(BaseModel):
    price: Decimal = Field(gt=0)
    quantity: int = Field(gt=0)
    tax: Decimal = 0
    commission: Decimal = 0
    date: datetime
    transaction_type: TransactionType


class NewStockTransaction(Transaction):
    stock_id: int


class StockTransaction(NewStockTransaction):
    stock_transaction_id: int


class StockTransactionHistory(BaseModel):
    transactions: List[StockTransaction]


class DetailedStock(Stock):
    market: str
    currency: str
    last_price: Decimal
    last_rate: Decimal


class TradedStocks(BaseModel):
    stocks: List[DetailedStock]
