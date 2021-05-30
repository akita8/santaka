from decimal import Decimal
from typing import List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
    fiscal_price: Decimal
    profit_and_loss: Decimal


class TradedStocks(BaseModel):
    stocks: List[DetailedStock]


class SplitEvent(BaseModel):
    date: datetime
    factor: int = Field(gt=0)
