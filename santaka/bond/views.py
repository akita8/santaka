from datetime import datetime
from decimal import Decimal

# from unittest import result

from fastapi import Depends, APIRouter

# from fastapi.param_functions import Query
# from sqlalchemy.sql import select
# from santaka.bond.models import BondTransaction

from santaka.db import (
    database,
    bonds,
    # currency,
    # bond_transactions,
    create_random_id,
    # users,
    # accounts,
    # owners,
)

from santaka.user import User, get_current_user

# from santaka.account import get_owner
from santaka.bond.models import DetailedBond, NewBond

# NewBondTransaction da aggiungere alla riga sopra quando sarà necessario
# from santaka.bond.utils import get_bond_data

router = APIRouter(prefix="/bond", tags=["bond"])
test_bond = {
    "Official Close": Decimal("107.2464"),
    "Official Close Date": datetime(2022, 5, 12, 0, 0),
    "Interest Rate": "",
    "Opening": Decimal("102.50"),
    "Last Volume": "8,000",
    "Total Quantity": "18,000",
    "Number Trades": Decimal("3"),
    "Day Low": Decimal("102.39"),
    "Day High": Decimal("103.49"),
    "Year Low": Decimal("100.00"),
    "Year High": Decimal("107.90"),
    "Gross yield to maturity": Decimal("2.93"),
    "Net yield to maturity": Decimal("2.84"),
    "Gross accrued interest": Decimal("0.11"),
    "Net accrued interest": Decimal("0.09625"),
    "Modified Duration": Decimal("4.25"),
    "Reference price": Decimal("103.06"),
    "Reference price date": "13/05/2022",
    "Isin Code": "IT0003934657",
    "Issuer": "World Bank",
    "Guarantor": "-",
    "Seniority": "SENIOR",
    "Tipology": "Supranational",
    "Bond Structure": "Plain Vanilla",
    "Outstanding": "65,000,000",
    "Lot Size": "2,000",
    "Negotiation Currency/ Settlement currency": "NZD/NZD",
    "Market": "MOT",
    "Clearing/Settlement": "-/Euroclear and Clearstream Banking Lussemburgo",
    "First Day of Trading": datetime(2005, 10, 14, 0, 0),
    "Credit Event": "",
    "Denomination": "'Btp-1fb37 4%",
    "Instrument ID": Decimal("808786"),
    "Interest Commencement Date": datetime(2017, 2, 7, 0, 0),
    "First Coupon Date": datetime(2006, 2, 1, 0, 0),
    "Last Payment Date": datetime(2022, 5, 6, 0, 0),
    "Expiry Date": datetime(2037, 2, 1, 0, 0),
    "Coupon Frequency": "Semiannually",
    "Trading Type": "Clean",
    "Day Count Convention": "30/360",
    "Next Coupon": Decimal("3.60"),
    "Call": "N.A",
    "Put": "N.A",
    "Payout Description": "",
}


@router.put("/", response_model=DetailedBond)
@database.transaction()
async def create_bond(new_bond: NewBond, user: User = Depends(get_current_user)):
    isin = new_bond.isin.upper()
    issuing_price = new_bond.issuing_price
    # create response dict from body model
    bond = new_bond.dict()

    # bond_records = await get_bond_data(isin)
    bond_records = test_bond
    # iso_currency = bond_records["Negotiation Currency/ Settlement currency"]

    # op-op-op-op-op-op-op-op-op-op-op-op - op-op-op-op-op-op-op-op-op-op-op-op

    # check if currency already exists in database
    # query = currency.select().where(currency.c.iso_currency == iso_currency)
    # currency_record = await database.fetch_one(query)

    # if currency_record is None:
    #     # handle if currency does not exist
    #     # if bond currency is the default one use last rate of 1
    #     last_rate = 1
    #     symbol = None
    #     if iso_currency != user.base_currency:
    #         # if bond currency is not the default one get bond data from utils
    #         #  to get currency info
    #         symbol = f"{user.base_currency}{iso_currency}=X".upper()
    #         currency_info = await call_yahoo_from_view(symbol)
    #         last_rate = currency_info[YAHOO_FIELD_PRICE]
    #     # save currency record in the database and get the record id
    #     query = currency.insert().values(
    #         currency_id=create_random_id(),
    #         iso_currency=iso_currency,
    #         last_rate=last_rate,
    #         symbol=symbol,
    #         last_update=datetime.utcnow(),
    #     )
    #     currency_id = await database.execute(query)

    # op-op-op-op-op-op-op-op-op-op-op-op - op-op-op-op-op-op-op-op-op-op-op-op

    bond_id = create_random_id()
    yearly_coupon_percent = 0
    if bond_records["Coupon Frequency"] == "Quarterly":
        yearly_coupon_percent = bond_records["Next Coupon"]
    if bond_records["Coupon Frequency"] == "Semiannually":
        yearly_coupon_percent = bond_records["Next Coupon"] * 2
    if bond_records["Coupon Frequency"] == "Annually":
        yearly_coupon_percent = bond_records["Next Coupon"]

    query = bonds.insert().values(
        bond_id=create_random_id(),
        isin=isin,
        market=bond_records["Market"],
        last_price=bond_records["Official Close"],
        currency_id=394660255759239,
        short_name=bond_records["Denomination"],
        expiry_date=bond_records["Expiry Date"],
        first_coupon_date=bond_records["First Coupon Date"],
        yearly_coupon_percent=yearly_coupon_percent,
        coupon_frequency=bond_records["Coupon Frequency"],
        issuing_date=bond_records["First Day of Trading"],
        issuing_price=issuing_price,
        # iso_currency=bond_records["Negotiation Currency/ Settlement currency"],
        net_yield_to_maturity=bond_records["Net yield to maturity"],
    )
    bond_id = await database.execute(query)
    bond["short_name"] = bond_records["Denomination"]
    # bond["iso_currency"] = bond_records["Negotiation Currency/ Settlement currency"]
    bond["bond_id"] = bond_id
    bond["isin"] = isin
    bond["market"] = bond_records["Market"]
    bond["last_price"] = bond_records["Official Close"]
    bond["expiry_date"] = bond_records["Expiry Date"]
    bond["first_coupon_date"] = bond_records["First Coupon Date"]
    bond["yearly_coupon_percent"] = yearly_coupon_percent
    bond["coupon_frequency"] = bond_records["Coupon Frequency"]
    bond["issuing_date"] = bond_records["First Day of Trading"]
    bond["net_yield_to_maturity"] = bond_records["Net yield to maturity"]

    return bond

    # return {
    #     "last_price": bond_records["Official Close"],
    #     "short_name": bond_records["Denomination"],
    #     "bond_id": bond_id,
    #     "market": bond_records["Market"],
    #     "maturity_date": bond_records["Expiry Date"],
    #     "issuing_date": bond_records["First Day of Trading"],
    #     "first_coupon_date": bond_records["First Coupon Date"],
    #     "coupon_frequency": bond_records["Coupon Frequency"],
    #     "issuing_price": issuing_price,
    #     "yearly_coupon_percent": yearly_coupon_percent,
    #     "iso_currency": bond_records["Negotiation Currency/ Settlement currency"],
    #     "net_yield_to_maturity": bond_records["Net yield to maturity"],
    # }


# @router.put(
#     "/transaction/{owner_id}/",
#     response_model=BondTransaction,
# )
# @database.transaction()
# async def create_bond_transaction(
#     owner_id: int,
#     bond_transaction_id: NewBondTransaction,
#     user: User = Depends(get_current_user),
# ):
# create bond record
# query = bonds.insert().values(
#     bond_id=create_random_id(),
#     name=bond_records["Denomination"],
#     coupon_frequency=bond_records["Coupon Frequency"],
#     last_price=bond_records["Official Close"],
#     issuing_date=bond_records["First Day of Trading"],
#     expiry_date=bond_records["Expiry Date"],
# )
# bond_id = await database.execute(query)
# bond[name] = bond_records["Denomination"]
# bond[last_price] = bond_records["Official Close"]

# return bond
