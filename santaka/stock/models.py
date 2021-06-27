from decimal import Decimal

from typing import List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NewStock(BaseModel):
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


class StockTransactionToDelete(BaseModel):
    stock_transaction_id: int


class StockTransactionToUpdate(BaseModel):
    stock_transaction_id: int
    price: Optional[Decimal] = Field(gt=0, default=None)
    quantity: Optional[int] = Field(gt=0, default=None)
    tax: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    date: Optional[datetime] = None


class StockToDelete(BaseModel):
    stock_id: int


class NewStockAlert(BaseModel):
    stock_id: int
    lower_limit_price: Optional[Decimal] = None
    upper_limit_price: Optional[Decimal] = None
    dividend_date: Optional[datetime] = None


class StockAlert(NewStockAlert):
    stock_alert_id: int


class StockAlerts(BaseModel):
    alerts: List[StockAlert]


class StockAlertToDelete(BaseModel):
    stock_alert_id: int


class AlertFields(str, Enum):
    LOWER_LIMIT_PRICE = "lower_limit_price"
    UPPER_LIMIT_PRICE = "upper_limit_price"
    DIVIDEND_DATE = "dividend_date"


class StockAlertToUpdate(BaseModel):
    stock_alert_id: int
    lower_limit_price: Optional[Decimal] = None
    upper_limit_price: Optional[Decimal] = None
    dividend_date: Optional[datetime] = None
    disabled_fields: Optional[List[AlertFields]] = None
