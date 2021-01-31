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
            response.error.message = "failed validation: price, quantity and last price must be greater than 0"
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
            response.error.message = "failed validation: price, invested and next coupon rate must be greater than 0"
            return response
        net_coupon = request.next_coupon_rate - request.next_coupon_tax
        maturity = datetime.fromtimestamp(request.maturity_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        day_to_repayment = (maturity - current).days
        if day_to_repayment <= 365.0:
            response.coupon_yield = 0
            return response
        if request.payment_frequency == santaka_pb2.PaymentFrequency.SIX_MONTHS:
            net_coupon = (request.next_coupon_rate - request.next_coupon_tax) * 2
        elif request.payment_frequency == santaka_pb2.PaymentFrequency.THREE_MONTHS:
            net_coupon = (request.next_coupon_rate - request.next_coupon_tax) * 4
        cumulative_coupon = (net_coupon / 365.0) * day_to_repayment
        cumulative_coupon *= request.invested
        repayment_diff = request.invested - (request.invested * (request.price / 100))
        yield_tot = int(cumulative_coupon + repayment_diff)
        response.coupon_yield = yield_tot / (day_to_repayment / 365.0)
        return response


class FiscalPriceService(santaka_grpc.FiscalPriceService):
    def _validate_transactions(self, transactions, response):
        if len(transactions) == 0:
            response.error.message = "failed validation: at least one transaction needed to calculate fiscal price"
            return response, True
        if transactions[0].operation != santaka_pb2.Operation.BUY:
            response.error.message = (
                "failed validation: the first transaction operation must be BUY"
            )
            return response, True
        return response, False

    def _validate_transaction(self, transaction, response):
        if transaction.price <= 0 or transaction.quantity <= 0:
            response.error.message = (
                "failed validation: price and quantity must be greater than 0"
            )
            return response, True
        return response, False

    def _process_transaction_sell(self, transaction, invested, current_quantity):
        new_quantity = current_quantity - transaction.quantity
        invested = (invested / current_quantity) * new_quantity
        return invested, new_quantity

    def _calculate_fiscal_price(self, invested, quantity):
        return invested / quantity

    def _process_split_event(self, factor, quantity, response, index):
        if factor == 0:
            response.error.message = (
                f"failed validation: error in split event number {index+1},"
                "factor must be greater than 0"
            )
            return quantity, response
        quantity = quantity * factor
        return quantity, response

    def CalculateStockFiscalPrice(self, request, *args):
        response = santaka_pb2.FiscalPriceResponse()
        invested = 0
        quantity = 0
        split_index = 0
        response, failed = self._validate_transactions(request.transactions, response)
        if failed:
            return response
        for transaction in request.transactions:
            response, failed = self._validate_transaction(transaction, response)
            if failed:
                return response
            if (
                split_index < len(request.split_events)
                and transaction.date > request.split_events[split_index].date
            ):
                quantity, response = self._process_split_event(
                    request.split_events[split_index].factor,
                    quantity,
                    response,
                    split_index,
                )
                if response.error.message:
                    return response
                split_index += 1
            if transaction.operation == santaka_pb2.Operation.BUY:
                quantity = quantity + transaction.quantity
                invested = invested + (
                    transaction.price * transaction.quantity + transaction.commission
                )
            elif transaction.operation == santaka_pb2.Operation.SELL:
                invested, quantity = self._process_transaction_sell(
                    transaction, invested, quantity
                )
        while split_index < len(request.split_events):
            quantity, response = self._process_split_event(
                request.split_events[split_index].factor,
                quantity,
                response,
                split_index,
            )
            if response.error.message:
                return response
            split_index += 1
        response.fiscal_price = self._calculate_fiscal_price(invested, quantity)
        return response

    def CalculateBondFiscalPrice(self, request, *args):
        response = santaka_pb2.FiscalPriceResponse()
        invested = 0
        quantity = 0
        response, failed = self._validate_transactions(request.transactions, response)
        if failed:
            return response
        for transaction in request.transactions:
            response, failed = self._validate_transaction(transaction, response)
            if failed:
                return response
            if transaction.operation == santaka_pb2.Operation.BUY:
                quantity = quantity + transaction.quantity
                invested = invested + transaction.price * transaction.quantity
            elif transaction.operation == santaka_pb2.Operation.SELL:
                invested, quantity = self._process_transaction_sell(
                    transaction, invested, quantity
                )
        response.fiscal_price = self._calculate_fiscal_price(invested, quantity)
        return response
