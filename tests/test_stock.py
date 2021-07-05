from datetime import datetime
from decimal import Decimal
from typing import List

from pytest import raises, mark, approx
from fastapi import HTTPException

from santaka.stock.utils import (
    YahooMarket,
    calculate_commission,
    calculate_sell_tax,
    get_active_markets,
    validate_stock_transaction,
)
from santaka.stock.models import NewStockTransaction, TransactionType
from santaka.account import Bank


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
            Bank.FINECOBANK.value,
            YahooMarket.ITALY.value,
            Decimal("200"),
            10,
            Decimal("3.8"),
        ],
        [
            Bank.FINECOBANK.value,
            YahooMarket.ITALY.value,
            Decimal("2150"),
            10,
            Decimal("19"),
        ],
        [
            Bank.FINECOBANK.value,
            YahooMarket.ITALY.value,
            Decimal("23"),
            10,
            Decimal("2.95"),
        ],
        [
            Bank.FINECOBANK.value,
            YahooMarket.EU.value,
            Decimal("99.98"),
            3,
            Decimal("2.95"),
        ],
        [
            Bank.FINECOBANK.value,
            YahooMarket.UK.value,
            Decimal("16.935"),
            60,
            Decimal("20.0305"),
        ],
        [
            Bank.FINECOBANK.value,
            YahooMarket.USA_NYSE.value,
            Decimal("216.5"),
            60,
            Decimal("12.95"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.ITALY.value,
            Decimal("44"),
            10,
            Decimal("2.5"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.ITALY.value,
            Decimal("100"),
            50,
            Decimal("8.5"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.ITALY.value,
            Decimal("440"),
            100,
            Decimal("17.5"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.EU.value,
            Decimal("44"),
            100,
            Decimal("11"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.UK.value,
            Decimal("16.935"),
            60,
            Decimal("16.0805"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.USA_NASDAQ.value,
            Decimal("44"),
            100,
            Decimal("11"),
        ],
        [
            Bank.BG_SAXO.value,
            YahooMarket.CANADA.value,
            Decimal("124"),
            30,
            Decimal("29.6"),
        ],
        [
            Bank.BANCA_GENERALI.value,
            YahooMarket.ITALY.value,
            Decimal("230"),
            10,
            Decimal("8"),
        ],
        [
            Bank.BANCA_GENERALI.value,
            YahooMarket.ITALY.value,
            Decimal("630"),
            10,
            Decimal("9.45"),
        ],
        [
            Bank.BANCA_GENERALI.value,
            YahooMarket.ITALY.value,
            Decimal("1630"),
            10,
            Decimal("20"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.ITALY.value,
            Decimal("11.1"),
            50,
            Decimal("6"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.ITALY.value,
            Decimal("75"),
            100,
            Decimal("13.5"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.ITALY.value,
            Decimal("150"),
            100,
            Decimal("25"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.EU.value,
            Decimal("11.1"),
            60,
            Decimal("12"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.EU.value,
            Decimal("75"),
            100,
            Decimal("13.5"),
        ],
        [
            Bank.CHE_BANCA.value,
            YahooMarket.EU.value,
            Decimal("200"),
            100,
            Decimal("35"),
        ],
        [
            None,
            YahooMarket.ITALY.value,
            Decimal("0"),
            100,
            Decimal("0"),
        ],
    ],
)
def test_calculate_commission(
    bank: str, market: str, price: Decimal, quantity: int, expected: Decimal
):
    commission = calculate_commission(bank, market, price, quantity)
    assert commission == expected


@mark.parametrize(
    ["market", "fiscal_price", "last_price", "quantity", "expected"],
    [
        [
            YahooMarket.ITALY.value,
            Decimal("13.4387"),
            Decimal("10.582"),
            75,
            Decimal("0"),
        ],
        [
            YahooMarket.ITALY.value,
            Decimal("24.7"),
            Decimal("39.57"),
            20,
            Decimal("77.324"),
        ],
        [
            YahooMarket.USA_NYSE.value,
            Decimal("118.59034"),
            Decimal("127.35"),
            5,
            Decimal("16.25"),
        ],
        [
            YahooMarket.CANADA.value,
            Decimal("42.19657"),
            Decimal("57.42"),
            140,
            Decimal("790.7297"),
        ],
        [
            YahooMarket.EU.value,
            Decimal("100.9633"),
            Decimal("233.3"),
            3,
            Decimal("179.6073"),
        ],
    ],
)
def test_calculate_sell_tax(
    market: str,
    fiscal_price: Decimal,
    last_price: Decimal,
    quantity: int,
    expected: Decimal,
):
    tax = calculate_sell_tax(market, fiscal_price, last_price, quantity)
    assert approx(tax, Decimal("0.001")) == expected


@mark.parametrize(
    ["dt", "expected_markets"],
    [
        [datetime(2021, 6, 11, 9, 0, 0, 0), ["LSE", "EXTRA", "Milan"]],
        [datetime(2021, 6, 16, 19, 0, 0, 0), ["NasdaqGS", "NYSE", "Toronto"]],
        [datetime(2021, 7, 4, 19, 0, 0, 0), []],
        [
            datetime(2021, 7, 6, 15, 0, 0, 0),
            ["NasdaqGS", "NYSE", "LSE", "EXTRA", "Milan", "Toronto"],
        ],
    ],
)  # TODO add some test cases
def test_get_active_markets(dt: datetime, expected_markets: List[str]):
    active_market = get_active_markets(dt)
    assert active_market == expected_markets
