from unittest.mock import MagicMock

from pytest import approx, mark

from engine.analytics import DifferenceService, AlertService, CouponYieldService
from engine.santaka_pb2 import (
    DifferenceRequest, PriceAlertRequest,
    ExpirationAlertRequest, Operation,
    CouponYieldRequest
)


@mark.parametrize('price,last_price,quantity,tax,on_buy,on_sell,expected, error_expected', [
    (6.96, 5.47, 100, 0.696, 3, 3, -155.7, False),
    (24.3, 34.04, 20, 0.494, 8, 8, 178.31, False),
    (0, 0, 0, 0, 0, 0, 0, True)
])
def test_calculate_stock_difference(
        price, last_price, quantity, tax, on_buy, on_sell, expected, error_expected):
    service = DifferenceService(MagicMock())
    request = DifferenceRequest()
    request.price = price
    request.last_price = last_price
    request.quantity = quantity
    request.tax = tax
    request.commission.on_buy = on_buy
    request.commission.on_sell = on_sell
    response = service.CalculateStockDifference(request)
    assert bool(response.error.message) is error_expected
    assert approx(response.difference, 0.01) == expected


def test_calculate_bond_difference():
    service = DifferenceService(MagicMock())
    request = DifferenceRequest()
    request.price = 99.88
    request.last_price = 100.332
    request.quantity = 3000
    request.tax = 0
    request.commission.on_buy = 5
    request.commission.on_sell = 5
    response = service.CalculateBondDifference(request)
    assert not response.error.message
    assert approx(response.difference, 0.01) == 3.56


@mark.parametrize('price,last_price,operation,message_expected,error_expected', [
    (13.5, 13.42, Operation.BUY, True, False),
    (13.42, 13.5, Operation.SELL, True, False),
    (13.5, 13.42, Operation.NOP, False, False),
    (0, 13.42, Operation.BUY, False, True),
])
def test_alert_check_price(price, last_price, operation, message_expected, error_expected):
    service = AlertService(MagicMock())
    request = PriceAlertRequest()
    request.price = price
    request.last_price = last_price
    request.operation = operation
    response = service.CheckPrice(request)
    assert bool(response.message) is message_expected
    assert bool(response.error.message) is error_expected


@mark.parametrize('expiration_date,current_date,message_expected', [
    (1608982515, 1609587567, True),
    (1612265967, 1609587567, False),
])
def test_alert_check_expiration(expiration_date, current_date, message_expected):
    service = AlertService(MagicMock())
    request = ExpirationAlertRequest()
    request.expiration_date = expiration_date
    request.current_date = current_date
    response = service.CheckExpiration(request)
    assert bool(response.message) is message_expected
    assert not response.error.message


@mark.parametrize(
    'price,maturity_date,current_date,next_coupon_rate,\
    invested,next_coupon_tax,error_expected,expected',
    [
        (100.332, 1616067567, 1609611915, 0.0125, 10000, 0.0015625, False, -49),
        (0, 1616067567, 1609611915, 0.0125, 10000, 0.0015625, True, 0)
    ]
)
def test_calculate_coupon_yield(
        price, maturity_date, current_date, next_coupon_rate,
        invested, next_coupon_tax, error_expected, expected):
    service = CouponYieldService(MagicMock())
    request = CouponYieldRequest()
    request.price = price
    request.maturity_date = maturity_date
    request.current_date = current_date
    request.next_coupon_rate = next_coupon_rate
    request.invested = invested
    request.next_coupon_tax = next_coupon_tax
    response = service.CalculateCouponYield(request)
    assert bool(response.error.message) is error_expected
    assert approx(response.coupon_yield, 0.01) == expected
