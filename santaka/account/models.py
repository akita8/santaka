from decimal import Decimal
from typing import List
from enum import Enum
from pydantic import BaseModel


class Owner(BaseModel):
    name: str
    owner_id: int


class NewOwner(BaseModel):
    account_id: int
    name: str


class OwnerDetails(Owner):
    bank_name: str
    account_number: str


class Bank(str, Enum):
    FINECOBANK = "fineco"
    BG_SAXO = "bg_saxo"
    BANCA_GENERALI = "banca_generali"
    CHE_BANCA = "che_banca"
    IWBANK = "iwbank"


BANK_NAMES = {
    Bank.FINECOBANK.value: "FinecoBank",
    Bank.BG_SAXO.value: "BG-Saxo",
    Bank.BANCA_GENERALI.value: "Banca Generali",
    Bank.CHE_BANCA.value: "Che Banca",
    Bank.IWBANK.value: "IwBank",
}


class NewAccount(BaseModel):
    bank: Bank
    account_number: str


class Account(NewAccount):
    account_id: int
    owners: List[Owner]
    bank_name: str
    current_stock_ctv: Decimal


class Accounts(BaseModel):
    accounts: List[Account]
