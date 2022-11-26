from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.sql import select

from santaka.db import (
    database,
    accounts,
    owners,
)
from santaka.stock.analytics import calculate_stock_totals
from santaka.stock.utils import (
    check_stock_alerts,
    get_transaction_records,
    prepare_traded_stocks,
)


async def get_owner(user_id: int, owner_id: int) -> Tuple[int, str, str, int, str]:
    # this query also checks that the owner exists
    # and that it's linked to one of the users accounts
    query = (
        select(
            [
                accounts.c.account_id,
                accounts.c.bank,
                accounts.c.account_number,
                owners.c.owner_id,
                owners.c.fullname,
            ]
        )
        .select_from(
            accounts.join(owners, accounts.c.account_id == owners.c.account_id),
        )
        .where(accounts.c.user_id == user_id)
        .where(owners.c.owner_id == owner_id)
    )
    record = await database.fetch_one(query)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Owner {owner_id} doesn't exist",
        )
    return record


async def calculate_stock_total_ctv(owner_id: int):
    records = await get_transaction_records([owner_id])
    traded_stocks = prepare_traded_stocks(records)
    _, _, current_stock_ctv, _ = calculate_stock_totals(traded_stocks)
    return current_stock_ctv


async def check_for_triggered_alerts(owner_id: int) -> bool:
    alerts = await check_stock_alerts(owner_id=owner_id)
    for a in alerts:
        if len(a["triggered_fields"]) > 0:
            return True
    return False
