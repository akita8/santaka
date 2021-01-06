from datetime import datetime, timedelta

import engine.santaka_pb2_grpc as santaka_grpc
import engine.santaka_pb2 as santaka_pb2


class DifferenceService(santaka_grpc.DifferenceService):
    def CalculateStockDifference(self, request, *args):
        return self._calculate_difference(request)

    def CalculateBondDifference(self, request, *args):
        request.price = request.price / 100
        request.last_price = request.last_price / 100
        return self._calculate_difference(request)

    def _calculate_difference(self, request):
        response = santaka_pb2.DifferenceResponse()
        if request.price <= 0 or request.quantity <= 0 or request.last_price <= 0:
            response.error.message = \
                'failed validation: price, quantity and last price must be greater than 0'
            return response
        bought = (
            request.quantity * request.price + request.commission.on_buy + request.tax
        )
        sold = request.quantity * request.last_price - request.commission.on_sell
        response.difference = sold - bought
        return response


class AlertService(santaka_grpc.AlertService):
    def CheckExpiration(self, request, *args):
        response = santaka_pb2.AlertResponse()
        expiration = datetime.fromtimestamp(request.expiration_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        if expiration - timedelta(2) <= current:
            response.message = "expired - less than 2 days from expiration date"
        return response

    def CheckPrice(self, request, *args):
        response = santaka_pb2.AlertResponse()
        if request.price <= 0 or request.last_price <= 0:
            response.error.message = (
                "failed validation: price and last price must be greater than 0"
            )
            return response
        if (
            request.operation == santaka_pb2.Operation.SELL
            and request.last_price >= request.price
        ):
            response.message = "sell - current price is greater than price set"
        if (
            request.operation == santaka_pb2.Operation.BUY
            and request.last_price <= request.price
        ):
            response.message = "buy - current price is lower than price set"
        return response


class CouponYieldService(santaka_grpc.CouponYieldService):
    def CalculateCouponYield(self, request, *args):
        response = santaka_pb2.CouponYieldResponse()
        if request.price <= 0 or request.next_coupon_rate <= 0 or request.invested <= 0:
            response.error.message = \
                'failed validation: price, invested and next coupon rate must be greater than 0'
            return response
        maturity = datetime.fromtimestamp(request.maturity_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        net_coupon = request.next_coupon_rate - request.next_coupon_tax
        day_to_repayment = (maturity - current).days
        cumulative_coupon = (net_coupon / 365.0) * day_to_repayment
        cumulative_coupon *= request.invested
        repayment_diff = request.invested - (request.invested * (request.price / 100))
        yield_tot = int(cumulative_coupon + repayment_diff)
        response.coupon_yield = yield_tot / (day_to_repayment / 365.0)
        return response


class FiscalPriceService(santaka_grpc.FiscalPriceService):
    def _calculate_fiscal_price(self, request, *args):
        response = santaka_pb2.FiscalPriceResponse()
        if len(request.transactions) == 0:
            response.error.message = \
                'failed validation: at least one transaction needed to calculate fiscal price'
            return response
        if request.transactions[0].operation != santaka_pb2.Operation.BUY:
            response.error.message = (
                "failed validation: the first transaction operation must be BUY"
            )
            return response
        invested = 0
        quantity = 0
        for transaction in request.transactions:
            if transaction.price <= 0 or transaction.quantity <= 0:
                response.error.message = (
                    "failed validation: price and quantity must be greater than 0"
                )
                return response
            if transaction.operation == santaka_pb2.Operation.BUY:
                quantity = quantity + transaction.quantity
                # handling missing bond commission
                try:
                    invested = invested + (
                        transaction.price * transaction.quantity
                        + transaction.commission
                    )
                except AttributeError:
                    invested = invested + transaction.price * transaction.quantity
            elif transaction.operation == santaka_pb2.Operation.SELL:
                new_quantity = quantity - transaction.quantity
                invested = (invested / quantity) * new_quantity
                quantity = new_quantity
        response.fiscal_price = invested / quantity
        return response

    def CalculateStockFiscalPrice(self, request, *args):
        return self._calculate_fiscal_price(request)

    def CalculateBondFiscalPrice(self, request, *args):
        return self._calculate_fiscal_price(request)
