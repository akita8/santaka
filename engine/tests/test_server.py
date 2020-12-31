from unittest.mock import MagicMock

from engine.santaka_pb2_grpc import google_dot_protobuf_dot_empty__pb2
from engine.server import Pinger


def test_pinger():
    p = Pinger(MagicMock())
    assert isinstance(p.Ping(), google_dot_protobuf_dot_empty__pb2.Empty)
