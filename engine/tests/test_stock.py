from unittest.mock import MagicMock

from pytest import approx, mark

from engine.stock import StockDifferenceService, StockAlertService
from engine.santaka_pb2 import (
    StockDifferenceRequest, StockPriceAlertRequest,
    StockExpirationAlertRequest, Operation
)


@mark.parametrize('price,last_price,quantity,tax,on_buy,on_sell,expected, error_expected', [
    (6.96, 5.47, 100, 0.696, 3, 3, -155.7, False),
    (24.3, 34.04, 20, 0.494, 8, 8, 178.31, False),
    (0, 0, 0, 0, 0, 0, 0, True)
])
def test_calculate_difference(
        price, last_price, quantity, tax, on_buy, on_sell, expected, error_expected):
    service = StockDifferenceService(MagicMock())
    request = StockDifferenceRequest()
    request.price = price
    request.last_price = last_price
    request.quantity = quantity
    request.tax = tax
    request.commission.on_buy = on_buy
    request.commission.on_sell = on_sell
    response = service.CalculateDifference(request)
    assert bool(response.error.message) is error_expected
    assert approx(response.difference, 0.01) == expected


@mark.parametrize('price,last_price,operation,message_expected,error_expected', [
    (13.5, 13.42, Operation.BUY, True, False),
    (13.42, 13.5, Operation.SELL, True, False),
    (13.5, 13.42, Operation.NOP, False, False),
    (0, 13.42, Operation.BUY, False, True),
])
def test_alert_check_price(price, last_price, operation, message_expected, error_expected):
    service = StockAlertService(MagicMock())
    request = StockPriceAlertRequest()
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
    service = StockAlertService(MagicMock())
    request = StockExpirationAlertRequest()
    request.expiration_date = expiration_date
    request.current_date = current_date
    response = service.CheckExpiration(request)
    assert bool(response.message) is message_expected
    assert not response.error.message
