import asyncio

import click

from santaka import utils


@click.command()
@click.option("-u", "--username", "username", type=str, required=True)
@click.option("-p", "--password", "password", type=str, required=True)
def create_user(username: str, password: str):
    asyncio.run(utils.create_user(username, password))
