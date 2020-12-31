import click

import engine.server


@click.command()
@click.option("-h", "--host", "host", type=str, default="127.0.0.1")
@click.option("-p", "--port", "port", type=int, default=50051)
@click.option("-w", "--max-workers", "max_workers", type=int, default=10)
@click.option("-l", "--log-level", "log_level", type=str, default="info")
def main(host, port, max_workers, log_level):
    engine.server.start(host, port, max_workers, log_level)
