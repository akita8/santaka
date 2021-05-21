from typing import List

from aiohttp import ClientSession

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"


async def get_yahoo_quote(symbols: List[str]):
    async with ClientSession() as session:
        async with session.get(
            YAHOO_QUOTE_URL, params={"symbols": ",".join(symbols)}
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
