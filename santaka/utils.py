from typing import List

from aiohttp import ClientSession

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"


class YahooError(Exception):
    pass


async def get_yahoo_quote(symbols: List[str]):
    async with ClientSession() as session:
        async with session.get(
            YAHOO_QUOTE_URL,
            params={"symbols": ",".join(symbols), "fields": "regularMarketPrice"},
        ) as resp:
            if resp.status != 200:
                raise YahooError()
            response = await resp.json()
    quotes = {}
    for quote in response["quoteResponse"]["result"]:
        quotes[quote["symbol"]] = quote["regularMarketPrice"]
    return quotes
