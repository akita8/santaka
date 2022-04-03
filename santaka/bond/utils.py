# from decimal import Decimal

# from sqlalchemy.sql import select

# from santaka.db import (
#     database,
#     bonds,
#     currency,
#     bond_transactions,
#     accounts,
#     owners,
#     bond_alerts,
# )


# async def get_bond_records(*isin: str):
#     query = select(
#         [
#             bonds.c.last_price,
#             bonds.c.short_name,
#             bonds.c.isin,
#             bonds.c.bond_id,
#             bonds.c.market,
#             bonds.c.currency_id,
#             currency.c.iso_currency,
#         ]
#     ).select_from(bonds.join(currency, bonds.c.currency_id == currency.c.currency_id))
#     if isin:
#         query = query.where(
#             bonds.c.isin.in_(isin),
#         )
#     return await database.fetch_all(query)
