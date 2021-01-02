from datetime import datetime, timedelta

import engine.santaka_pb2_grpc as santaka_grpc
import engine.santaka_pb2 as santaka_pb2


class LoggerMixin:
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger


class DifferenceService(santaka_grpc.DifferenceService, LoggerMixin):

    def CalculateStockDifference(self, request, *args):
        return self._calculate_difference(request)

    def CalculateBondDifference(self, request, *args):
        request.price = request.price/100
        request.last_price = request.last_price/100
        return self._calculate_difference(request)

    def _calculate_difference(self, request):
        response = santaka_pb2.DifferenceResponse()
        if request.price <= 0 or request.quantity <= 0 or request.last_price <= 0:
            response.error.message = \
                'failed validation: price, quantity and last price must be greater than 0'
            return response
        bought = request.quantity * request.price + request.commission.on_buy + request.tax
        sold = request.quantity * request.last_price - request.commission.on_sell
        response.difference = sold - bought
        return response


class AlertService(santaka_grpc.AlertService, LoggerMixin):
    def CheckExpiration(self, request, *args):
        response = santaka_pb2.AlertResponse()
        expiration = datetime.fromtimestamp(request.expiration_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        if expiration - timedelta(2) <= current:
            response.message = 'expired - less than 2 days from expiration date'
        return response

    def CheckPrice(self, request, *args):
        response = santaka_pb2.AlertResponse()
        if request.price <= 0 or request.last_price <= 0:
            response.error.message = \
                'failed validation: price and last price must be greater than 0'
            return response
        if request.operation == santaka_pb2.Operation.SELL and request.last_price >= request.price:
            response.message = 'sell - current price is greater than price set'
        if request.operation == santaka_pb2.Operation.BUY and request.last_price <= request.price:
            response.message = 'buy - current price is lower than price set'
        return response


class CouponYieldService(santaka_grpc.CouponYieldService, LoggerMixin):
    def CalculateCouponYield(self, request, *args):
        response = santaka_pb2.CouponYieldResponse()
        if request.price <= 0 or request.next_coupon_rate <= 0 or request.invested <= 0:
            response.error.message = \
                'failed validation: price, invested and next coupon rate must be greater than 0'
            return response
        maturity = datetime.fromtimestamp(request.maturity_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        net_coupon = request.next_coupon_rate - request.next_coupon_tax
        day_to_repayment = (maturity-current).days
        cumulative_coupon = (net_coupon/365.0)*day_to_repayment
        cumulative_coupon *= request.invested
        repayment_diff = request.invested - (request.invested*(request.price/100))
        yield_tot = int(cumulative_coupon + repayment_diff)
        response.coupon_yield = yield_tot/(day_to_repayment/365.0)
        return response
