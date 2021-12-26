from decimal import Decimal
from typing import List, Optional, Tuple

from santaka.stock.models import (
    TradedStock,
    Transaction,
    TransactionType,
    SplitEvent,
)


def calculate_profit_and_loss(
    fiscal_price: Decimal,
    last_price: Decimal,
    sell_tax: Decimal,
    sell_commission: Decimal,
    quantity: int,
) -> Decimal:
    invested = quantity * fiscal_price
    sold = quantity * last_price - sell_commission - sell_tax
    return sold - invested


def calculate_invested(
    fiscal_price: Decimal, fiscal_price_converted: Decimal, quantity: int
) -> Tuple[Decimal, Decimal]:
    invested = quantity * fiscal_price
    invested_converted = quantity * fiscal_price_converted
    return invested, invested_converted


def calculate_ctvs(
    last_price: Decimal, last_rate: Decimal, quantity: int
) -> Tuple[Decimal, Decimal]:
    current_ctv = quantity * last_price
    current_ctv_converted = current_ctv / last_rate
    return current_ctv, current_ctv_converted


def calculate_stock_totals(
    traded_stocks: List[TradedStock],
) -> Tuple[Decimal, Decimal, Decimal]:
    invested_converted = 0
    profit_and_loss_converted = 0
    current_ctv_converted = 0
    for stock in traded_stocks:
        invested_converted += stock["invested_converted"]
        profit_and_loss_converted += stock["profit_and_loss_converted"]
        current_ctv_converted += stock["current_ctv_converted"]

    return invested_converted, profit_and_loss_converted, current_ctv_converted


def calculate_fiscal_price(
    transactions: List[Transaction], split_events: Optional[List[SplitEvent]] = None
) -> Tuple[Decimal, Decimal]:
    invested = 0
    invested_converted = 0
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
            invested_converted = (
                invested_converted
                + (transaction.price * transaction.quantity + transaction.commission)
                / transaction.transaction_ex_rate
            )
        elif transaction.transaction_type == TransactionType.sell:
            new_quantity = quantity - transaction.quantity
            invested = (invested / quantity) * new_quantity
            invested_converted = (invested_converted / quantity) * new_quantity
            quantity = new_quantity
    while split_events and split_index < len(split_events):
        quantity = split_events[split_index].factor * quantity
        split_index += 1
    return invested / quantity, invested_converted / quantity


# class CouponYieldService(santaka_grpc.CouponYieldService):
#     def CalculateCouponYield(self, request, *args):
#         response = santaka_pb2.CouponYieldResponse()
#         if request.price <= 0 or request.next_coupon_rate <= 0
#           or request.invested <= 0:
#           response.error.message = "failed validation: price, invested and next
#           coupon rate must be greater than 0"
#           return response
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
