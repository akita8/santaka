# from decimal import Decimal
# from datetime import datetime
# import decimal


# from pydantic import BaseModel

# from santaka.stock.models import Transaction


# class NewBond(BaseModel):
#     isin: str


# class Bond(BaseModel):
#     short_name: str
#     bond_id: int
#     market: str
#     last_price: decimal
#     currency_id: int
#     iso_currency: str
#     maturity_date: datetime
#     yearly_coupon_percent: Decimal
#     first_coupon_date: datetime
#     coupon_frequency: decimal
#     coupon_tax: Decimal


# class BondTransaction(Transaction):
#     pass
