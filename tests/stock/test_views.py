from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from pytest import mark, approx

from santaka.stock.views import prepare_traded_stocks, TransactionRecords
from santaka.stock.utils import YahooMarket
from santaka.stock.models import TransactionType
from santaka.account import Bank


@mark.parametrize(
    ["transaction_records", "bank", "expected_stocks"],
    [
        [[], Bank.FINECOBANK.value, []],
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
                ),
            ],
            Bank.FINECOBANK.value,
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
                ),
            ],
            Bank.FINECOBANK.value,
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
                ),
            ],
            Bank.CHE_BANCA.value,
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
        #         ),
        #     ],
        #     Bank.CHE_BANCA.value,
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
    bank: str,
    expected_stocks: List[Dict],
):
    traded_stocks = prepare_traded_stocks(transaction_records, bank)

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
