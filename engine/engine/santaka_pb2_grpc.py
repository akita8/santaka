# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
import engine.santaka_pb2 as santaka__pb2


class PingerStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Ping = channel.unary_unary(
                '/santaka.Pinger/Ping',
                request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
                response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                )


class PingerServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Ping(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PingerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Ping': grpc.unary_unary_rpc_method_handler(
                    servicer.Ping,
                    request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                    response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'santaka.Pinger', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Pinger(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Ping(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/santaka.Pinger/Ping',
            google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)


class StockDifferenceServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.CalculateDifference = channel.unary_unary(
                '/santaka.StockDifferenceService/CalculateDifference',
                request_serializer=santaka__pb2.StockDifferenceRequest.SerializeToString,
                response_deserializer=santaka__pb2.StockDifferenceResponse.FromString,
                )


class StockDifferenceServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def CalculateDifference(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_StockDifferenceServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'CalculateDifference': grpc.unary_unary_rpc_method_handler(
                    servicer.CalculateDifference,
                    request_deserializer=santaka__pb2.StockDifferenceRequest.FromString,
                    response_serializer=santaka__pb2.StockDifferenceResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'santaka.StockDifferenceService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class StockDifferenceService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def CalculateDifference(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/santaka.StockDifferenceService/CalculateDifference',
            santaka__pb2.StockDifferenceRequest.SerializeToString,
            santaka__pb2.StockDifferenceResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)


class StockAlertServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.CheckPrice = channel.unary_unary(
                '/santaka.StockAlertService/CheckPrice',
                request_serializer=santaka__pb2.StockPriceAlertRequest.SerializeToString,
                response_deserializer=santaka__pb2.StockAlertResponse.FromString,
                )
        self.CheckExpiration = channel.unary_unary(
                '/santaka.StockAlertService/CheckExpiration',
                request_serializer=santaka__pb2.StockExpirationAlertRequest.SerializeToString,
                response_deserializer=santaka__pb2.StockAlertResponse.FromString,
                )


class StockAlertServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def CheckPrice(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CheckExpiration(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_StockAlertServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'CheckPrice': grpc.unary_unary_rpc_method_handler(
                    servicer.CheckPrice,
                    request_deserializer=santaka__pb2.StockPriceAlertRequest.FromString,
                    response_serializer=santaka__pb2.StockAlertResponse.SerializeToString,
            ),
            'CheckExpiration': grpc.unary_unary_rpc_method_handler(
                    servicer.CheckExpiration,
                    request_deserializer=santaka__pb2.StockExpirationAlertRequest.FromString,
                    response_serializer=santaka__pb2.StockAlertResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'santaka.StockAlertService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class StockAlertService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def CheckPrice(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/santaka.StockAlertService/CheckPrice',
            santaka__pb2.StockPriceAlertRequest.SerializeToString,
            santaka__pb2.StockAlertResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def CheckExpiration(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/santaka.StockAlertService/CheckExpiration',
            santaka__pb2.StockExpirationAlertRequest.SerializeToString,
            santaka__pb2.StockAlertResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
