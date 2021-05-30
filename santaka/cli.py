import asyncio

import click

from santaka import user


@click.command()
@click.option("-u", "--username", "username", type=str, required=True)
@click.option("-p", "--password", "password", type=str, required=True)
@click.option("-c", "--base-currency", "base_currency", type=str, default="EUR")
def create_user(username: str, password: str, base_currency: str):
    asyncio.run(user.create_user(username, password, base_currency))
