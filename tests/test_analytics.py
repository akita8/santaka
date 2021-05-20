# from decimal import Decimal

# from pytest import approx, mark


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


# @mark.parametrize(
#     "transactions,expected_fiscal_price,error_expected",
#     (
#         (
#             (
#                 (Operation.BUY, 5, 108.62, 11.97),
#                 (Operation.SELL, 2, 277, 12.13),
#                 (Operation.BUY, 2, 262.94, 11.97),
#             ),
#             174.1784,
#             False,
#         ),
#         (
#             (
#                 (
#                     Operation.BUY,
#                     500,
#                     3.994,
#                     8,
#                 ),
#                 (
#                     Operation.BUY,
#                     500,
#                     3.6,
#                     8,
#                 ),
#                 (Operation.SELL, 900, 4.58, 0),
#                 (Operation.SELL, 100, 4.579, 8),
#                 (
#                     Operation.BUY,
#                     1000,
#                     4.4,
#                     8,
#                 ),
#                 (Operation.SELL, 500, 4.84, 8),
#                 (Operation.SELL, 500, 4.887, 8),
#                 (
#                     Operation.BUY,
#                     700,
#                     4.073,
#                     8,
#                 ),
#                 (Operation.SELL, 700, 4.77, 8),
#                 (Operation.BUY, 200, 4.33, 8),
#                 (Operation.BUY, 500, 4.26, 8),
#             ),
#             4.3029,
#             False,
#         ),
#         (
#             ((Operation.BUY, 3, 151.1799, 12.5), (Operation.BUY, 2, 296.981, 11.99)),
#             214.3983,
#             False,
#         ),
#         ((), 0, True),
#         (((Operation.SELL, 2, 100, 12),), 0, True),
#         (((Operation.BUY, -5, 100, 8),), 0, True),
#     ),
# )
# def test_calculate_stock_fiscal_price(
#     transactions, expected_fiscal_price, error_expected
# ):
#     service = FiscalPriceService()
#     request = StockFiscalPriceRequest()
#     for transaction in transactions:
#         transaction_obj = request.transactions.add()
#         transaction_obj.operation = transaction[0]
#         transaction_obj.quantity = transaction[1]
#         transaction_obj.price = transaction[2]
#         transaction_obj.commission = transaction[3]
#     response = service.CalculateStockFiscalPrice(request)
#     assert approx(response.fiscal_price, 0.01) == expected_fiscal_price
#     assert bool(response.error.message) is error_expected


# @mark.parametrize(
#     "transactions,expected_fiscal_price,error_expected",
#     (
#         (
#             (
#                 (Operation.BUY, 2000, 99.93),
#                 (Operation.BUY, 1000, 99.53),
#                 (Operation.BUY, 1000, 99.98),
#             ),
#             99.8425,
#             False,
#         ),
#     ),
# )
# def test_calculate_bond_fiscal_price(
#     transactions, expected_fiscal_price, error_expected
# ):
#     service = FiscalPriceService()
#     request = BondFiscalPriceRequest()
#     for transaction in transactions:
#         transaction_obj = request.transactions.add()
#         transaction_obj.operation = transaction[0]
#         transaction_obj.quantity = transaction[1]
#         transaction_obj.price = transaction[2]
#     response = service.CalculateBondFiscalPrice(request)
#     assert approx(response.fiscal_price, 0.01) == expected_fiscal_price
#     assert bool(response.error.message) is error_expected
