from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.sql import select

from santaka.db import (
    database,
    accounts,
    owners,
    users,
)
from santaka.user import User, get_current_user
from santaka.db import create_random_id
from santaka.account.utils import calculate_stock_total_ctv, get_owner
from santaka.account.models import (
    Account,
    Accounts,
    BANK_NAMES,
    NewAccount,
    NewOwner,
    Owner,
    OwnerDetails,
)

router = APIRouter(prefix="/account", tags=["account"])


@router.put("/owner/", response_model=Owner)
@database.transaction()
async def create_owner(new_owner: NewOwner, user: User = Depends(get_current_user)):
    query = (
        accounts.select()
        .where(accounts.c.user_id == user.user_id)
        .where(accounts.c.account_id == new_owner.account_id)
    )
    record = await database.fetch_one(query)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {new_owner.account_id} doesn't exist",
        )
    query = owners.insert().values(
        owner_id=create_random_id(),
        account_id=new_owner.account_id,
        fullname=new_owner.name,
    )
    owner_id = await database.execute(query)

    return {"name": new_owner.name, "owner_id": owner_id}


@router.put("/", response_model=Account)
@database.transaction()
async def create_account(
    new_account: NewAccount, user: User = Depends(get_current_user)
):
    query = accounts.insert().values(
        account_id=create_random_id(),
        account_number=new_account.account_number,
        bank=new_account.bank,
        user_id=user.user_id,
    )
    account_id = await database.execute(query)

    account = new_account.dict()
    account["account_id"] = account_id
    account["bank_name"] = BANK_NAMES[new_account.bank]
    account["owners"] = []
    account["current_ctv_converted"] = 0
    return account


@router.get("/", response_model=Accounts)
async def get_accounts(user: User = Depends(get_current_user)):
    query = (
        select(
            [
                accounts.c.bank,
                accounts.c.account_id,
                accounts.c.account_number,
                owners.c.fullname,
                owners.c.owner_id,
            ]
        )
        .select_from(
            users.join(accounts, users.c.user_id == accounts.c.user_id).outerjoin(
                owners, accounts.c.account_id == owners.c.account_id
            ),
        )
        .where(users.c.user_id == user.user_id)
    )
    records = await database.fetch_all(query)
    account_models = []
    previous_account_id = None
    for record in records:
        if record[1] != previous_account_id:
            bank_name = BANK_NAMES[record[0]]
            owners_ = []
            current_stock_ctv = 0
            if record[4] is not None:
                owners_ = [{"name": record[3], "owner_id": record[4]}]
                current_stock_ctv = await calculate_stock_total_ctv(record[4])
            account_models.append(
                {
                    "bank": record[0],
                    "account_number": record[2],
                    "account_id": record[1],
                    "owners": owners_,
                    "bank_name": bank_name,
                    "current_stock_ctv": current_stock_ctv,
                }
            )
        else:
            account_models[-1]["owners"].append(
                {"name": record[3], "owner_id": record[4]}
            )
            account_models[-1]["current_stock_ctv"] += await calculate_stock_total_ctv(
                record[4]
            )
        previous_account_id = record[1]

    return {"accounts": account_models}


@router.get("/owner/{owner_id}", response_model=OwnerDetails)
async def get_owners_detail(owner_id: int, user: User = Depends(get_current_user)):
    owner = await get_owner(user.user_id, owner_id)
    bank_name = BANK_NAMES[owner[1]]
    return {
        "owner_id": owner_id,
        "name": owner[4],
        "bank_name": bank_name,
        "account_number": owner[2],
    }
