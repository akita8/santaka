import concurrent.futures as futures
import grpc
import logging

import engine.santaka_pb2_grpc as santaka_grpc

from engine.analytics import DifferenceService, AlertService, CouponYieldService, FiscalPriceService


class Pinger(santaka_grpc.PingerServicer):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def Ping(self, *args):
        self.logger.debug("ping")
        return santaka_grpc.google_dot_protobuf_dot_empty__pb2.Empty()


def add_grpc_services(server, logger):
    santaka_grpc.add_PingerServicer_to_server(Pinger(logger), server)
    santaka_grpc.add_DifferenceServiceServicer_to_server(
        DifferenceService(),
        server
    )
    santaka_grpc.add_AlertServiceServicer_to_server(
        AlertService(),
        server
    )
    santaka_grpc.add_CouponYieldServiceServicer_to_server(
        CouponYieldService(),
        server
    )
    santaka_grpc.add_FiscalPriceServiceServicer_to_server(
        FiscalPriceService(),
        server
    )


def setup_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("engine")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def start(host: str, port: int, max_workers: int, log_level: str):
    logger = setup_logger(log_level)
    address = f"{host}:{port}"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers))
    add_grpc_services(server, logger)
    server.add_insecure_port(address)
    server.start()
    logger.info("santaka engine server listening on %s", address)
    server.wait_for_termination()
