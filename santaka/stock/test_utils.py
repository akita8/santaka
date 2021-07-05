from decimal import Decimal

from datetime import datetime

from pytest import mark

from santaka.stock.utils import (
    check_dividend_date,
    check_fiscal_price_lower_than,
    check_fiscal_price_greater_than,
    check_profit_and_loss_upper_limit,
    check_lower_limit_price,
    check_upper_limit_price,
)


def test_check_dividend_date():
    answer = check_dividend_date(datetime(2021, 3, 22))
    assert not answer


def test_check_fiscal_price_lower_than():
    answer = check_fiscal_price_lower_than(Decimal("10"), Decimal("11"))
    assert not answer


def test_check_fiscal_price_greater_than():
    answer = check_fiscal_price_greater_than(Decimal("11"), Decimal("10"))
    assert not answer


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
