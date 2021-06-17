import asyncio
import logging

from santaka.stock.utils import update_stocks, update_currency, YAHOO_UPDATE_COOLDOWN

logger = logging.getLogger(__name__)


async def run_periodic_update(name, update_func, cooldown):
    while True:
        try:
            await update_func()
        except Exception as e:
            logger.error(
                "update func %s error: %s, retrying in %d seconds",
                name,
                e,
                cooldown,
            )
        await asyncio.sleep(cooldown)


async def run_tasks():
    asyncio.create_task(
        run_periodic_update("stocks", update_stocks, YAHOO_UPDATE_COOLDOWN)
    )
    asyncio.create_task(
        run_periodic_update("currency", update_currency, YAHOO_UPDATE_COOLDOWN)
    )
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_tasks())
