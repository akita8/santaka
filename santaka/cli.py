import asyncio

import click

from santaka.app import create_user as _create_user


@click.command()
@click.option("-u", "--username", "username", type=str, required=True)
@click.option("-p", "--password", "password", type=str, required=True)
def create_user(username, password: str):
    asyncio.run(_create_user(username, password))
