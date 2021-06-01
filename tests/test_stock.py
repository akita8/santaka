from datetime import datetime
from decimal import Decimal
from pytest import raises, mark

from santaka.stock.utils import calculate_commission, validate_stock_transaction
from santaka.stock.models import NewStockTransaction, TransactionType
from fastapi import HTTPException


class FakeRecord:
    def __init__(self, transaction_type, quantity):
        self.transaction_type = transaction_type
        self.quantity = quantity


def test_first_transaction_not_buy():
    with raises(HTTPException):
        validate_stock_transaction(
            [],
            NewStockTransaction(
                price=1,
                quantity=1,
                date=datetime.now(),
                transaction_type=TransactionType.sell,
                stock_id=1,
            ),
        )


def test_total_quantity_greater_than_sell():
    with raises(HTTPException):
        validate_stock_transaction(
            [FakeRecord(TransactionType.buy, 1)],
            NewStockTransaction(
                price=1,
                quantity=2,
                date=datetime.now(),
                transaction_type=TransactionType.sell,
                stock_id=1,
            ),
        )


@mark.parametrize(
    ["bank", "market", "price", "quantity", "expected"],
    [
        [
            "fineco",
            "milan",
            Decimal("20.50"),
            10,
            Decimal("0"),
        ],  # this an example test case, add more
    ],
)
def test_calculate_commission(
    bank: str, market: str, price: Decimal, quantity: int, expected: Decimal
):
    commission = calculate_commission(bank, market, price, quantity)
    assert commission == expected


def test_calculate_stamp_europe():
    pass


def test_calculate_stamp_uk():
    pass
