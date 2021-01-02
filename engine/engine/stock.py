from datetime import datetime, timedelta

import engine.santaka_pb2_grpc as santaka_grpc
import engine.santaka_pb2 as santaka_pb2


class LoggerMixin:
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger


class StockDifferenceService(santaka_grpc.StockDifferenceService, LoggerMixin):

    def CalculateDifference(self, request, *args):
        response = santaka_pb2.StockDifferenceResponse()
        if request.price <= 0 or request.quantity <= 0 or request.last_price <= 0:
            response.error.message = \
                'failed validation: price, quantity and last price must be greater than 0'
            return response
        bought = request.quantity * request.price + request.commission.on_buy + request.tax
        sold = request.quantity * request.last_price - request.commission.on_sell
        response.difference = sold - bought
        return response


class StockAlertService(santaka_grpc.StockAlertService, LoggerMixin):
    def CheckExpiration(self, request, *args):
        response = santaka_pb2.StockAlertResponse()
        expiration = datetime.fromtimestamp(request.expiration_date).date()
        current = datetime.fromtimestamp(request.current_date).date()
        if expiration - timedelta(2) <= current:
            response.message = 'expired - less than 2 days from expiration date'
        return response

    def CheckPrice(self, request, *args):
        response = santaka_pb2.StockAlertResponse()
        if request.price <= 0 or request.last_price <= 0:
            response.error.message = \
                'failed validation: price and last price must be greater than 0'
            return response
        if request.operation == santaka_pb2.Operation.SELL and request.last_price >= request.price:
            response.message = 'sell - current price is greater than price set'
        if request.operation == santaka_pb2.Operation.BUY and request.last_price <= request.price:
            response.message = 'buy - current price is lower than price set'
        return response
