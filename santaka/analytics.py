from decimal import Decimal
from typing import List, Optional

# from datetime import datetime, timedelta

from santaka.models import Transaction, TransactionType, SplitEvent


def calculate_profit_and_loss(
    fiscal_price, last_price, buy_tax, sell_tax, sell_commission: Decimal, quantity: int
) -> Decimal:
    # TODO implement tests (see test/test_analytics.py)
    bought = quantity * fiscal_price + buy_tax
    sold = quantity * last_price - sell_commission - sell_tax
    return sold - bought


def calculate_fiscal_price(
    transactions: List[Transaction], split_events: Optional[List[SplitEvent]] = None
) -> Decimal:
    invested = 0
    quantity = 0
    split_index = 0
    for transaction in transactions:
        if (
            split_events
            and split_index < len(split_events)
            and transaction.date > split_events[split_index].date
        ):
            quantity = split_events[split_index].factor * quantity
            split_index += 1
        if transaction.transaction_type == TransactionType.buy:
            quantity = quantity + transaction.quantity
            invested = invested + (
                transaction.price * transaction.quantity + transaction.commission
            )
        elif transaction.transaction_type == TransactionType.sell:
            new_quantity = quantity - transaction.quantity
            invested = (invested / quantity) * new_quantity
            quantity = new_quantity
    while split_events and split_index < len(split_events):
        quantity = split_events[split_index].factor * quantity
        split_index += 1
    return invested / quantity


# class AlertService(santaka_grpc.AlertService):
#     def CheckExpiration(self, request, *args):
#         response = santaka_pb2.AlertResponse()
#         expiration = datetime.fromtimestamp(request.expiration_date).date()
#         current = datetime.fromtimestamp(request.current_date).date()
#         if expiration - timedelta(2) <= current:
#             response.message = "expired - less than 2 days from expiration date"
#         return response

#     def CheckPrice(self, request, *args):
#         response = santaka_pb2.AlertResponse()
#         if request.price <= 0 or request.last_price <= 0:
#             response.error.message = (
#                 "failed validation: price and last price must be greater than 0"
#             )
#             return response
#         if (
#             request.operation == santaka_pb2.Operation.SELL
#             and request.last_price >= request.price
#         ):
#             response.message = "sell - current price is greater than price set"
#         if (
#             request.operation == santaka_pb2.Operation.BUY
#             and request.last_price <= request.price
#         ):
#             response.message = "buy - current price is lower than price set"
#         return response


# class CouponYieldService(santaka_grpc.CouponYieldService):
#     def CalculateCouponYield(self, request, *args):
#         response = santaka_pb2.CouponYieldResponse()
#         if request.price <= 0 or request.next_coupon_rate <= 0 or request.invested <= 0:
#             response.error.message = "failed validation: price, invested and next coupon rate must be greater than 0"
#             return response
#         net_coupon = request.next_coupon_rate - request.next_coupon_tax
#         maturity = datetime.fromtimestamp(request.maturity_date).date()
#         current = datetime.fromtimestamp(request.current_date).date()
#         day_to_repayment = (maturity - current).days
#         if day_to_repayment <= 365.0:
#             response.coupon_yield = 0
#             return response
#         if request.payment_frequency == santaka_pb2.PaymentFrequency.SIX_MONTHS:
#             net_coupon = (request.next_coupon_rate - request.next_coupon_tax) * 2
#         elif request.payment_frequency == santaka_pb2.PaymentFrequency.THREE_MONTHS:
#             net_coupon = (request.next_coupon_rate - request.next_coupon_tax) * 4
#         cumulative_coupon = (net_coupon / 365.0) * day_to_repayment
#         cumulative_coupon *= request.invested
#         repayment_diff = request.invested - (request.invested * (request.price / 100))
#         yield_tot = int(cumulative_coupon + repayment_diff)
#         response.coupon_yield = yield_tot / (day_to_repayment / 365.0)
#         return response
