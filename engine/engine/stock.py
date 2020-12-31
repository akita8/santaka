import engine.santaka_pb2_grpc as santaka_grpc
import engine.santaka_pb2 as santaka_pb2


class StockDifferenceService(santaka_grpc.StockDifferenceService):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def CalculateDifference(self, request, *args):
        self.logger.debug("calculating difference")
        response = santaka_pb2.StockDifferenceResponse()
        return response
