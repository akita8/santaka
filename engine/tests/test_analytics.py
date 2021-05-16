from pytest import approx, mark

from engine.analytics import (
    DifferenceService,
    AlertService,
    CouponYieldService,
    FiscalPriceService,
)
from engine.santaka_pb2 import (
    DifferenceRequest,
    PriceAlertRequest,
    ExpirationAlertRequest,
    Operation,
    CouponYieldRequest,
    StockFiscalPriceRequest,
    BondFiscalPriceRequest,
    PaymentFrequency,
)


@mark.parametrize(
    "price,last_price,quantity,tax,on_buy,on_sell,expected, error_expected",
    [
        (6.96, 5.47, 100, 0.696, 3, 3, -155.7, False),
        (24.3, 34.04, 20, 0.494, 8, 8, 178.31, False),
        (0, 0, 0, 0, 0, 0, 0, True),
    ],
)
def test_calculate_stock_difference(
    price, last_price, quantity, tax, on_buy, on_sell, expected, error_expected
):
    service = DifferenceService()
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
    service = DifferenceService()
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


@mark.parametrize(
    "price,last_price,operation,message_expected,error_expected",
    [
        (13.5, 13.42, Operation.BUY, True, False),
        (13.42, 13.5, Operation.SELL, True, False),
        (13.5, 13.42, Operation.NOP, False, False),
        (0, 13.42, Operation.BUY, False, True),
    ],
)
def test_alert_check_price(
    price, last_price, operation, message_expected, error_expected
):
    service = AlertService()
    request = PriceAlertRequest()
    request.price = price
    request.last_price = last_price
    request.operation = operation
    response = service.CheckPrice(request)
    assert bool(response.message) is message_expected
    assert bool(response.error.message) is error_expected


@mark.parametrize(
    "expiration_date,current_date,message_expected",
    [
        (1608982515, 1609587567, True),
        (1612265967, 1609587567, False),
    ],
)
def test_alert_check_expiration(expiration_date, current_date, message_expected):
    service = AlertService()
    request = ExpirationAlertRequest()
    request.expiration_date = expiration_date
    request.current_date = current_date
    response = service.CheckExpiration(request)
    assert bool(response.message) is message_expected
    assert not response.error.message


@mark.parametrize(
    "price,maturity_date,current_date,next_coupon_rate,\
    invested,next_coupon_tax,payment_frequency,error_expected,expected",
    [
        (
            100.15,
            1616067567,
            1611435962,
            0.0125,
            10000,
            0.0015625,
            PaymentFrequency.SIX_MONTHS,
            False,
            0,
        ),
        (
            0,
            1616067567,
            1609611915,
            0.0125,
            10000,
            0.0015625,
            PaymentFrequency.ONE_YEAR,
            True,
            0,
        ),
        (
            132.0329,
            3066233698,
            1610619080,
            0.028,
            10000,
            0.0035,
            PaymentFrequency.ONE_YEAR,
            False,
            175.17,
        ),
        (
            126.94,
            1898590280,
            1610619080,
            0.035,
            10000,
            0.004375,
            PaymentFrequency.ONE_YEAR,
            False,
            11.23,
        ),
        (
            132.0329,
            3066233698,
            1610619080,
            0.014,
            10000,
            0.00175,
            PaymentFrequency.SIX_MONTHS,
            False,
            175.17,
        ),
        (
            114.2407,
            1801947962,
            1611435962,
            0.009,
            10000,
            0.001125,
            PaymentFrequency.THREE_MONTHS,
            False,
            79.27,
        ),
    ],
)
def test_calculate_coupon_yield(
    price,
    maturity_date,
    current_date,
    next_coupon_rate,
    invested,
    next_coupon_tax,
    payment_frequency,
    error_expected,
    expected,
):
    service = CouponYieldService()
    request = CouponYieldRequest()
    request.price = price
    request.maturity_date = maturity_date
    request.current_date = current_date
    request.next_coupon_rate = next_coupon_rate
    request.invested = invested
    request.next_coupon_tax = next_coupon_tax
    request.payment_frequency = payment_frequency
    response = service.CalculateCouponYield(request)
    assert bool(response.error.message) is error_expected
    assert approx(response.coupon_yield, 0.01) == expected


@mark.parametrize(
    "transactions,split_events,expected_fiscal_price,error_expected",
    (
        (
            (
                (Operation.BUY, 5, 108.62, 11.97, 0),
                (Operation.SELL, 2, 277, 12.13, 0),
                (Operation.BUY, 2, 262.94, 11.97, 0),
            ),
            [],
            174.1784,
            False,
        ),
        (
            (
                (Operation.BUY, 50, 31.65, 15.19, 0),
                (Operation.BUY, 30, 46.71, 16.76, 0),
                (Operation.BUY, 20, 51.78, 15.98, 0),
                (Operation.BUY, 20, 50.00, 17.08, 0),
                (Operation.BUY, 20, 40.30, 17.09, 0),
            ),
            [],
            42.196,
            False,
        ),
        (
            (
                (Operation.BUY, 500, 3.994, 8, 0),
                (Operation.BUY, 500, 3.6, 8, 0),
                (Operation.SELL, 900, 4.58, 0, 0),
                (Operation.SELL, 100, 4.579, 8, 0),
                (Operation.BUY, 1000, 4.4, 8, 0),
                (Operation.SELL, 500, 4.84, 8, 0),
                (Operation.SELL, 500, 4.887, 8, 0),
                (Operation.BUY, 700, 4.073, 8, 0),
                (Operation.SELL, 700, 4.77, 8, 0),
                (Operation.BUY, 200, 4.33, 8, 0),
                (Operation.BUY, 500, 4.26, 8, 0),
            ),
            [],
            4.3029,
            False,
        ),
        (
            (
                (Operation.BUY, 3, 151.1799, 12.5, 0),
                (Operation.BUY, 2, 296.981, 11.99, 0),
            ),
            [],
            214.3983,
            False,
        ),
        ((), [], 0, True),
        (((Operation.SELL, 2, 100, 12, 0),), [], 0, True),
        (((Operation.BUY, -5, 100, 8, 0),), [], 0, True),
        (
            (
                (Operation.BUY, 3, 151.1799, 12.5, 1546036022),
                (Operation.BUY, 2, 296.981, 11.99, 1582928822),
            ),
            [(1598826422, 4)],
            53.598,
            False,
        ),
        (
            (
                (Operation.BUY, 3, 151.1799, 12.5, 1546036022),
                (Operation.BUY, 2, 296.981, 11.99, 1582928822),
                (Operation.BUY, 5, 132.000, 11.99, 1612202877)
            ),
            [(1598826422, 4)],
            69.7585,
            False,
        ),
    ),
)
def test_calculate_stock_fiscal_price(
    transactions, split_events, expected_fiscal_price, error_expected
):
    service = FiscalPriceService()
    request = StockFiscalPriceRequest()
    for transaction in transactions:
        transaction_obj = request.transactions.add()
        transaction_obj.operation = transaction[0]
        transaction_obj.quantity = transaction[1]
        transaction_obj.price = transaction[2]
        transaction_obj.commission = transaction[3]
        transaction_obj.date = transaction[4]
    for split in split_events:
        split_obj = request.split_events.add()
        split_obj.date = split[0]
        split_obj.factor = split[1]
    response = service.CalculateStockFiscalPrice(request)
    assert approx(response.fiscal_price, 0.01) == expected_fiscal_price
    assert bool(response.error.message) is error_expected


@mark.parametrize(
    "transactions,expected_fiscal_price,error_expected",
    (
        (
            (
                (Operation.BUY, 2000, 99.93),
                (Operation.BUY, 1000, 99.53),
                (Operation.BUY, 1000, 99.98),
            ),
            99.8425,
            False,
        ),
        (
            (
                (Operation.BUY, 1000, 95.76),
                (Operation.BUY, 1000, 93.76),
                (Operation.BUY, 2000, 99.94),
                (Operation.BUY, 2000, 99.27),
                (Operation.SELL, 1000, 91.09),
                (Operation.SELL, 1000, 92.89),
                (Operation.SELL, 1000, 93.92),
                (Operation.BUY, 1000, 89.37),
                (Operation.SELL, 1000, 81.95),
                (Operation.SELL, 1000, 100.02),
            ),
            95.835,
            False,
        ),
    ),
)
def test_calculate_bond_fiscal_price(
    transactions, expected_fiscal_price, error_expected
):
    service = FiscalPriceService()
    request = BondFiscalPriceRequest()
    for transaction in transactions:
        transaction_obj = request.transactions.add()
        transaction_obj.operation = transaction[0]
        transaction_obj.quantity = transaction[1]
        transaction_obj.price = transaction[2]
    response = service.CalculateBondFiscalPrice(request)
    assert approx(response.fiscal_price, 0.01) == expected_fiscal_price
    assert bool(response.error.message) is error_expected
