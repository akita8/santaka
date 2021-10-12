from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from pytest import mark, approx

from santaka.stock.utils import YahooMarket, prepare_traded_stocks, TransactionRecords
from santaka.stock.models import TransactionType
from santaka.account import Bank

from santaka.stock.utils import (
    check_dividend_date,
    check_fiscal_price_lower_than,
    check_fiscal_price_greater_than,
    check_profit_and_loss_upper_limit,
    check_lower_limit_price,
    check_upper_limit_price,
)


@mark.parametrize(
    ["transaction_records", "expected_stocks"],
    [
        [[], []],
        [
            [
                (
                    1,
                    "USD",
                    Decimal("1.186521"),
                    "MDLZ",
                    Decimal("62.14"),
                    YahooMarket.USA_NASDAQ.value,
                    TransactionType.buy.value,
                    10,
                    Decimal("46"),
                    Decimal("3.94"),
                    datetime(2020, 3, 24),
                    Decimal("0"),
                    Bank.FINECOBANK.value,
                    1,
                    "USD",
                    "mondalez",
                    1,
                ),
            ],
            [
                {
                    "fiscal_price": Decimal("46.394"),
                    "profit_and_loss": Decimal("86.09234"),
                }
            ],
        ],
        [
            [
                (
                    2,
                    "EURO",
                    Decimal("1"),
                    "LDO.MI",
                    Decimal("6.98"),
                    YahooMarket.ITALY.value,
                    TransactionType.buy.value,
                    50,
                    Decimal("5.93"),
                    Decimal("2.95"),
                    datetime(2020, 5, 14),
                    Decimal("0"),
                    Bank.FINECOBANK.value,
                    1,
                    "EURO",
                    "leonardo",
                    1,
                ),
            ],
            [
                {
                    "fiscal_price": Decimal("5.989"),
                    "profit_and_loss": Decimal("33.717"),
                }
            ],
        ],
        [
            [
                (
                    3,
                    "USD",
                    Decimal("1.1944"),
                    "LMT",
                    Decimal("377.73"),
                    YahooMarket.USA_NYSE.value,
                    TransactionType.buy.value,
                    2,
                    Decimal("335.488"),
                    Decimal("14.734"),
                    datetime(2021, 1, 12),
                    Decimal("0"),
                    Bank.CHE_BANCA.value,
                    1,
                    "USD",
                    "lockeed martin",
                    1,
                ),
            ],
            [
                {
                    "fiscal_price": Decimal("342.855"),
                    "profit_and_loss": Decimal("31.8728"),
                }
            ],
        ],
        # [
        #     [
        #         (
        #             4,
        #             "CAD",
        #             Decimal("1.46679"),
        #             "CAR-UN.TO",
        #             Decimal("57.28"),
        #             YahooMarket.CANADA.value,
        #             TransactionType.buy.value,
        #             2,
        #             Decimal("335.488"),
        #             Decimal("14.734"),
        #             datetime(2021, 1, 12),
        #             Decimal("0"),
        #             Bank.CHE_BANCA.value,
        #             1,
        #         ),
        #     ],
        #     [
        #         {
        #             "fiscal_price": Decimal("342.855"),
        #             "profit_and_loss": Decimal("31.8728"),
        #         }
        #     ],
        # ],
    ],
)
def test_prepare_traded_stocks(
    transaction_records: List[TransactionRecords],
    expected_stocks: List[Dict],
):
    traded_stocks = prepare_traded_stocks(transaction_records)

    assert len(traded_stocks) == len(expected_stocks)

    for i, stock in enumerate(traded_stocks):
        assert (
            approx(stock["fiscal_price"], Decimal("0.001"))
            == expected_stocks[i]["fiscal_price"]
        )
        assert (
            approx(stock["profit_and_loss"], Decimal("0.001"))
            == expected_stocks[i]["profit_and_loss"]
        )


def test_check_dividend_date():
    answer = check_dividend_date(datetime(2021, 3, 22))
    assert answer


def test_check_fiscal_price_lower_than():
    answer = check_fiscal_price_lower_than(Decimal("10"), Decimal("11"))
    assert answer


def test_check_fiscal_price_greater_than():
    answer = check_fiscal_price_greater_than(Decimal("11"), Decimal("10"))
    assert answer


def test_check_profit_and_loss_greater_than():
    answer = check_profit_and_loss_upper_limit(Decimal("150"), Decimal("120"))
    assert not answer


@mark.parametrize(
    "last_price,lower_limit_price,expected_boolean",
    ((100, 200, True), (250, 125, False)),
)
def test_check_lower_limit_price(last_price, lower_limit_price, expected_boolean):
    answer = check_lower_limit_price(last_price, lower_limit_price)
    assert answer is expected_boolean


@mark.parametrize(
    "last_price,upper_limit_price,expected_boolean",
    ((350, 220, True), (150, 225, False)),
)
def test_check_upper_limit_price(last_price, upper_limit_price, expected_boolean):
    answer = check_upper_limit_price(last_price, upper_limit_price)
    assert answer is expected_boolean
