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
    owner_id: int


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


class AlertFields(str, Enum):
    LOWER_LIMIT_PRICE = "lower_limit_price"
    UPPER_LIMIT_PRICE = "upper_limit_price"
    DIVIDEND_DATE = "dividend_date"
    FISCAL_PRICE_LOWER_THAN = "fiscal_price_lower_than"
    FISCAL_PRICE_GREATER_THAN = "fiscal_price_greater_than"
    PROFIT_AND_LOSS_LOWER_LIMIT = "profit_and_loss_lower_limit"
    PROFIT_AND_LOSS_UPPER_LIMIT = "profit_and_loss_upper_limit"


class NewStockAlert(BaseModel):
    stock_id: int
    owner_id: int
    lower_limit_price: Optional[Decimal] = None
    upper_limit_price: Optional[Decimal] = None
    dividend_date: Optional[datetime] = None
    fiscal_price_lower_than: Optional[bool] = None
    fiscal_price_greater_than: Optional[bool] = None
    profit_and_loss_lower_limit: Optional[Decimal] = None
    profit_and_loss_upper_limit: Optional[Decimal] = None


class StockAlert(NewStockAlert):
    stock_alert_id: int
    triggered_fields: Optional[List[AlertFields]] = None


class StockAlerts(BaseModel):
    alerts: List[StockAlert]


class StockAlertToDelete(BaseModel):
    stock_alert_id: int


class StockAlertToUpdate(BaseModel):
    stock_alert_id: int
    lower_limit_price: Optional[Decimal] = None
    upper_limit_price: Optional[Decimal] = None
    dividend_date: Optional[datetime] = None
    fiscal_price_lower_than: Optional[bool] = None
    fiscal_price_greater_than: Optional[bool] = None
    profit_and_loss_lower_limit: Optional[Decimal] = None
    profit_and_loss_upper_limit: Optional[Decimal] = None
    disabled_fields: Optional[List[AlertFields]] = None
