from typing import List, Tuple
from enum import Enum

from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.sql import select
from pydantic import BaseModel, conlist

from santaka.db import (
    database,
    accounts,
    owners,
    users,
)
from santaka.user import User, get_current_user
from santaka.db import create_random_id

router = APIRouter(prefix="/account", tags=["account"])


class Owner(BaseModel):
    name: str
    owner_id: int


class OwnerDetails(Owner):
    bank_name: str
    account_number: str


class Bank(str, Enum):
    FINECOBANK = "fineco"
    BG_SAXO = "bg_saxo"
    BANCA_GENERALI = "banca_generali"
    CHE_BANCA = "che_banca"


BANK_NAMES = {
    Bank.FINECOBANK.value: "FinecoBank",
    Bank.BG_SAXO.value: "BG-Saxo",
    Bank.BANCA_GENERALI.value: "Banca Generali",
    Bank.CHE_BANCA.value: "Che Banca",
}


class NewAccount(BaseModel):
    owners: conlist(str, min_items=1)
    bank: Bank
    account_number: str
    bank_name: str


class Account(NewAccount):
    account_id: int
    owners: List[Owner]


class Accounts(BaseModel):
    accounts: List[Account]


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


@router.post("/", response_model=Account)
@database.transaction()
async def create_account(
    new_account: NewAccount, user: User = Depends(get_current_user)
):
    # TODO refactor by splitting in two views account creation and owner creation
    query = accounts.insert().values(
        account_id=create_random_id(),
        account_number=new_account.account_number,
        bank=new_account.bank,
        user_id=user.user_id,
    )
    account_id = await database.execute(query)
    new_owners = []
    for owner in new_account.owners:
        query = owners.insert().values(
            owner_id=create_random_id(),
            account_id=account_id,
            fullname=owner,
        )
        owner_id = await database.execute(query)
        new_owners.append({"owner_id": owner_id, "name": owner})
    account = new_account.dict()
    account["account_id"] = account_id
    account["owners"] = new_owners
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
            users.join(accounts, users.c.user_id == accounts.c.user_id).join(
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
            account_models.append(
                {
                    "bank": record[0],
                    "account_number": record[2],
                    "account_id": record[1],
                    "owners": [{"name": record[3], "owner_id": record[4]}],
                    "bank_name": bank_name,
                }
            )
        else:
            account_models[-1]["owners"].append(
                {"name": record[3], "owner_id": record[4]}
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
