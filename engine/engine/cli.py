import pathlib

import click
import grpc_tools
import pkg_resources

import engine.server


@click.command()
@click.option("-h", "--host", "host", type=str, default="127.0.0.1")
@click.option("-p", "--port", "port", type=int, default=50051)
@click.option("-w", "--max-workers", "max_workers", type=int, default=10)
@click.option("-l", "--log-level", "log_level", type=str, default="info")
def server(host, port, max_workers, log_level):
    engine.server.start(host, port, max_workers, log_level)


@click.command()
def generate():
    root = pathlib.Path(__file__).parent.parent.parent
    proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')
    args = [
        "",
        f"-I{root}",
        f"-I{proto_include}",
        "--python_out=engine",
        "--grpc_python_out=engine",
        str(root / "santaka.proto")]
    grpc_tools.protoc.main(args)
    with open(pathlib.Path(__file__).parent / "santaka_pb2_grpc.py", "r") as f:
        santaka_pb2_grpc = f.read().replace(
            "import santaka_pb2 as santaka__pb2",
            "import engine.santaka_pb2 as santaka__pb2"
        )
    with open(pathlib.Path(__file__).parent / "santaka_pb2.py", "r") as f:
        santaka_pb2 = f.read()
    with open(pathlib.Path(__file__).parent / "santaka_pb2_grpc.py", "w") as f:
        f.write("# flake8: noqa\n" + santaka_pb2_grpc)
    with open(pathlib.Path(__file__).parent / "santaka_pb2.py", "w") as f:
        f.write("# flake8: noqa\n" + santaka_pb2)
