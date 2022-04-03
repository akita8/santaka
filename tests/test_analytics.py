from datetime import datetime
from decimal import Decimal as D

from pytest import approx, mark

from santaka.stock.models import TransactionType, Transaction, SplitEvent
from santaka.stock.analytics import calculate_fiscal_price, calculate_profit_and_loss

# @mark.parametrize(
#     "price,last_price,operation,message_expected,error_expected",
#     [
#         (13.5, 13.42, TransactionType.buy, True, False),
#         (13.42, 13.5, TransactionType.sell, True, False),
#         (13.5, 13.42, Operation.NOP, False, False),
#         (0, 13.42, TransactionType.buy, False, True),
#     ],
# )
# def test_alert_check_price(
#     price, last_price, operation, message_expected, error_expected
# ):
#     service = AlertService()
#     request = PriceAlertRequest()
#     request.price = price
#     request.last_price = last_price
#     request.operation = operation
#     response = service.CheckPrice(request)
#     assert bool(response.message) is message_expected
#     assert bool(response.error.message) is error_expected


# @mark.parametrize(
#     "expiration_date,current_date,message_expected",
#     [
#         (1608982515, 1609587567, True),
#         (1612265967, 1609587567, False),
#     ],
# )
# def test_alert_check_expiration(expiration_date, current_date, message_expected):
#     service = AlertService()
#     request = ExpirationAlertRequest()
#     request.expiration_date = expiration_date
#     request.current_date = current_date
#     response = service.CheckExpiration(request)
#     assert bool(response.message) is message_expected
#     assert not response.error.message


# @mark.parametrize(
#     "price,maturity_date,current_date,next_coupon_rate,\
#     invested,next_coupon_tax,error_expected,expected",
#     [
#         (100.332, 1616067567, 1609611915, 0.0125, 10000, 0.0015625, False, -49),
#         (0, 1616067567, 1609611915, 0.0125, 10000, 0.0015625, True, 0),
#     ],
# )
# def test_calculate_coupon_yield(
#     price,
#     maturity_date,
#     current_date,
#     next_coupon_rate,
#     invested,
#     next_coupon_tax,
#     error_expected,
#     expected,
# ):
#     service = CouponYieldService()
#     request = CouponYieldRequest()
#     request.price = price
#     request.maturity_date = maturity_date
#     request.current_date = current_date
#     request.next_coupon_rate = next_coupon_rate
#     request.invested = invested
#     request.next_coupon_tax = next_coupon_tax
#     response = service.CalculateCouponYield(request)
#     assert bool(response.error.message) is error_expected
#     assert approx(response.coupon_yield, 0.01) == expected


@mark.parametrize(
    "transactions,split_events,expected_fiscal_price,expected_fiscal_price_converted",
    (
        (
            (
                (TransactionType.buy, 5, D("108.62"), D("11.97"), 0, D("1.08623")),
                (TransactionType.sell, 2, D("277"), D("12.13"), 0, D("1.10212")),
                (TransactionType.buy, 2, D("262.94"), D("11.97"), 0, D("1.0876")),
            ),
            [],
            D("174.1784"),
            D("160.144"),  # UNH stock and BG_Saxo account
        ),
        (
            (
                (TransactionType.buy, 50, D("31.65"), D("15.19"), 0, D("1.38112")),
                (TransactionType.buy, 30, D("46.71"), D("16.76"), 0, D("1.52219")),
                (TransactionType.buy, 20, D("51.78"), D("15.98"), 0, D("1.45164")),
                (TransactionType.buy, 20, D("50.00"), D("17.08"), 0, D("1.55304")),
                (TransactionType.buy, 20, D("40.30"), D("17.09"), 0, D("1.5474")),
            ),
            [],
            D("42.196"),
            D("28.5604"),  # CAR-UN.TO stock and BG_Saxo account
        ),
        (
            (
                (TransactionType.buy, 500, D("3.994"), D("8"), 0, 1),
                (TransactionType.buy, 500, D("3.6"), D("8"), 0, 1),
                (TransactionType.sell, 900, D("4.58"), D("0"), 0, 1),
                (TransactionType.sell, 100, D("4.579"), D("8"), 0, 1),
                (TransactionType.buy, 1000, D("4.4"), D("8"), 0, 1),
                (TransactionType.sell, 500, D("4.84"), D("8"), 0, 1),
                (TransactionType.sell, 500, D("4.887"), D("8"), 0, 1),
                (TransactionType.buy, 700, D("4.073"), D("8"), 0, 1),
                (TransactionType.sell, 700, D("4.77"), D("8"), 0, 1),
                (TransactionType.buy, 200, D("4.33"), D("8"), 0, 1),
                (TransactionType.buy, 500, D("4.26"), D("8"), 0, 1),
            ),
            [],
            D("4.3029"),
            D("4.3029"),  # SRG.MI stock and BG617 account
        ),
        (
            (
                (
                    TransactionType.buy,
                    3,
                    D("151.1799"),
                    D("12.5"),
                    1546036022,
                    D("1.13477"),
                ),
                (
                    TransactionType.buy,
                    2,
                    D("296.981"),
                    D("11.99"),
                    1582928822,
                    D("1.0876"),
                ),
            ),
            [(1598826422, 4)],
            D("53.598"),
            D("48.339"),  # AAPL stock and BG_Saxo account
        ),
        (
            (
                (TransactionType.buy, 3, D("151.1799"), D("12.5"), 1546036022, 1),
                (TransactionType.buy, 2, D("296.981"), D("11.99"), 1582928822, 1),
                (TransactionType.buy, 5, D("132.000"), D("11.99"), 1612202877, 1),
            ),
            [(1598826422, 4)],
            D("69.7585"),
            D("69.7585"),  # AAPL stock and BG_Saxo account with an extra buy
        ),
        (
            (
                (TransactionType.buy, 2000, D("99.93"), 0, 0, 1),
                (TransactionType.buy, 1000, D("99.53"), 0, 0, 1),
                (TransactionType.buy, 1000, D("99.98"), 0, 0, 1),
            ),
            None,
            D("99.8425"),
            D("99.8425"),
        ),
        (
            (
                (TransactionType.buy, 1000, D("95.76"), 0, 0, 1),
                (TransactionType.buy, 1000, D("93.76"), 0, 0, 1),
                (TransactionType.buy, 2000, D("99.94"), 0, 0, 1),
                (TransactionType.buy, 2000, D("99.27"), 0, 0, 1),
                (TransactionType.sell, 1000, D("91.09"), 0, 0, 1),
                (TransactionType.sell, 1000, D("92.89"), 0, 0, 1),
                (TransactionType.sell, 1000, D("93.92"), 0, 0, 1),
                (TransactionType.buy, 1000, D("89.37"), 0, 0, 1),
                (TransactionType.sell, 1000, D("81.95"), 0, 0, 1),
                (TransactionType.sell, 1000, D("100.02"), 0, 0, 1),
            ),
            None,
            D("95.835"),
            D("95.835"),
        ),
    ),
)
def test_calculate_stock_fiscal_price(
    transactions, split_events, expected_fiscal_price, expected_fiscal_price_converted
):
    transaction_dicts = []
    for transaction in transactions:
        transaction_dicts.append(
            Transaction(
                transaction_type=transaction[0],
                quantity=transaction[1],
                price=transaction[2],
                commission=transaction[3],
                date=datetime.fromtimestamp(transaction[4]),
                transaction_ex_rate=transaction[5],
            )
        )
    split_events_dicts = None
    if split_events:
        split_events_dicts = []
        for event in split_events:
            split_events_dicts.append(
                SplitEvent(date=datetime.fromtimestamp(event[0]), factor=event[1])
            )
    fiscal_price, fiscal_price_converted = calculate_fiscal_price(
        transaction_dicts, split_events_dicts
    )
    assert approx(fiscal_price, D("0.01")) == expected_fiscal_price
    assert approx(fiscal_price_converted, D("0.01")) == expected_fiscal_price_converted


@mark.parametrize(
    [
        # these are the names of the parameters the test will expect
        # (can also be passed as a string of comma separated names)
        "fiscal_price",
        "last_price",
        "sell_tax",
        "sell_commission",
        "quantity",
        "expected_profit_and_loss",
    ],
    [  # this is the list of test cases
        [
            D("24.7"),
            D("38.59"),
            D("0"),
            D("8"),
            20,
            D("269.8"),
        ],  # first test case, put adeguate parameters in this list these are
        [
            D("174.1784"),
            D("394.225"),
            D("408.19"),
            D("11"),
            5,
            D("681.046"),
        ],
        [
            D("46.394"),
            D("62.65"),
            D("60.3"),
            D("12.95"),
            10,
            D("89.3"),
        ],
        [
            D("342.855"),
            D("377.73"),
            D("25.88"),
            D("12"),
            2,
            D("31.87"),
        ],
    ],
)
def test_calculate_profit_and_loss(
    fiscal_price,
    last_price,
    sell_tax,
    sell_commission,
    quantity,
    expected_profit_and_loss,
    # last_rate,
):
    # To implement the test import the function you want to test
    # then call the function with the correct parameters
    # (hint: look at the function signature)
    # than assert that the result is the correct one (hint: look at other tests)
    result = calculate_profit_and_loss(
        fiscal_price,
        last_price,
        sell_tax,
        sell_commission,
        quantity,
    )
    assert approx(result, D("0.01")) == expected_profit_and_loss


# @mark.parametrize(
#     "price,last_price,operation,message_expected,error_expected",
#     [
#         (13.5, 13.42, Operation.BUY, True, False),
#         (13.42, 13.5, Operation.SELL, True, False),
#         (13.5, 13.42, Operation.NOP, False, False),
#         (0, 13.42, Operation.BUY, False, True),
#     ],
# )
# def test_alert_check_price(
#     price, last_price, operation, message_expected, error_expected
# ):
#     service = AlertService()
#     request = PriceAlertRequest()
#     request.price = price
#     request.last_price = last_price
#     request.operation = operation
#     response = service.CheckPrice(request)
#     assert bool(response.message) is message_expected
#     assert bool(response.error.message) is error_expected


# @mark.parametrize(
#     "expiration_date,current_date,message_expected",
#     [
#         (1608982515, 1609587567, True),
#         (1612265967, 1609587567, False),
#     ],
# )
# def test_alert_check_expiration(expiration_date, current_date, message_expected):
#     service = AlertService()
#     request = ExpirationAlertRequest()
#     request.expiration_date = expiration_date
#     request.current_date = current_date
#     response = service.CheckExpiration(request)
#     assert bool(response.message) is message_expected
#     assert not response.error.message


# @mark.parametrize(
#     "price,maturity_date,current_date,next_coupon_rate,\
#     invested,next_coupon_tax,payment_frequency,error_expected,expected",
#     [
#         (
#             100.15,
#             1616067567,
#             1611435962,
#             0.0125,
#             10000,
#             0.0015625,
#             PaymentFrequency.SIX_MONTHS,
#             False,
#             0,
#         ),
#         (
#             0,
#             1616067567,
#             1609611915,
#             0.0125,
#             10000,
#             0.0015625,
#             PaymentFrequency.ONE_YEAR,
#             True,
#             0,
#         ),
#         (
#             132.0329,
#             3066233698,
#             1610619080,
#             0.028,
#             10000,
#             0.0035,
#             PaymentFrequency.ONE_YEAR,
#             False,
#             175.17,
#         ),
#         (
#             126.94,
#             1898590280,
#             1610619080,
#             0.035,
#             10000,
#             0.004375,
#             PaymentFrequency.ONE_YEAR,
#             False,
#             11.23,
#         ),
#         (
#             132.0329,
#             3066233698,
#             1610619080,
#             0.014,
#             10000,
#             0.00175,
#             PaymentFrequency.SIX_MONTHS,
#             False,
#             175.17,
#         ),
#         (
#             114.2407,
#             1801947962,
#             1611435962,
#             0.009,
#             10000,
#             0.001125,
#             PaymentFrequency.THREE_MONTHS,
#             False,
#             79.27,
#         ),
#     ],
# )
# def test_calculate_coupon_yield(
#     price,
#     maturity_date,
#     current_date,
#     next_coupon_rate,
#     invested,
#     next_coupon_tax,
#     payment_frequency,
#     error_expected,
#     expected,
# ):
#     service = CouponYieldService()
#     request = CouponYieldRequest()
#     request.price = price
#     request.maturity_date = maturity_date
#     request.current_date = current_date
#     request.next_coupon_rate = next_coupon_rate
#     request.invested = invested
#     request.next_coupon_tax = next_coupon_tax
#     request.payment_frequency = payment_frequency
#     response = service.CalculateCouponYield(request)
#     assert bool(response.error.message) is error_expected
#     assert approx(response.coupon_yield, 0.01) == expected
