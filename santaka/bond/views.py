# from datetime import datetime

# from fastapi import status, HTTPException, Depends, APIRouter

# from fastapi.param_functions import Query
# from sqlalchemy.sql import select

# from santaka.db import (
#     database,
#     bonds,
#     currency,
#     bond_transactions,
#     create_random_id,
#     users,
#     accounts,
#     owners,
# )
# from santaka.user import User, get_current_user

# from santaka.account import get_owner
# from santaka.bond.models import NewBond, Bond
# from santaka.bond.utils import get_bond_records

# router = APIRouter(prefix="/bond", tags=["bond"])


# @router.put("/", response_model=Bond)
# @database.transaction()
# async def create_bond(new_bond: NewBond, user: User = Depends(get_current_user)):
#     bond_isin = new_bond.isin.upper()
#     bond_records = await get_bond_records(bond_isin)
#     bond = new_bond.dict()
