from datetime import datetime

from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy.sql import select

from santaka.db import (
    database,
    stocks,
    currency,
    stock_transactions,
    create_random_id,
)
from santaka.user import User, get_current_user
from santaka.account import get_owner
from santaka.analytics import calculate_fiscal_price, calculate_profit_and_loss
from santaka.stock.models import (
    NewStock,
    Stock,
    StockToDelete,
    TransactionType,
    Transaction,
    NewStockTransaction,
    StockTransaction,
    StockTransactionHistory,
    TradedStocks,
    StockTransactionToDelete,
    StockTransactionToUpdate,
)
from santaka.stock.utils import (
    calculate_commission,
    calculate_sell_tax,
    call_yahoo_from_view,
    validate_stock_transaction,
    YAHOO_FIELD_CURRENCY,
    YAHOO_FIELD_MARKET,
    YAHOO_FIELD_PRICE,
)

router = APIRouter(prefix="/stock", tags=["stock"])


@router.put("/", response_model=Stock)
@database.transaction()
async def create_stock(new_stock: NewStock, user: User = Depends(get_current_user)):
    # query the database to check if stock already exists
    query = (
        stocks.select()
        .where(
            stocks.c.isin == new_stock.isin
        )  # TODO maybe make isin symbol composite primary key
        .where(stocks.c.symbol == new_stock.symbol)
    )
    stock_record = await database.fetch_one(query)

    if stock_record is None:
        # stock not found in the database, calling yahoo to get stock info
        stock_symbol = new_stock.symbol.upper()
        stock_info = await call_yahoo_from_view(stock_symbol)
        iso_currency = stock_info[YAHOO_FIELD_CURRENCY]

        # check if currency already exists in database
        query = currency.select().where(currency.c.iso_currency == iso_currency)
        currency_record = await database.fetch_one(query)

        if currency_record is None:
            # handle if currency does not exist
            # if stock currency is the default one use last rate of 1
            last_rate = 1
            symbol = None
            if iso_currency != user.base_currency:
                # if stock currency is not the default one call yahoo
                #  to get currency info
                symbol = f"{user.base_currency}{iso_currency}=X".upper()
                currency_info = await call_yahoo_from_view(symbol)
                last_rate = currency_info[YAHOO_FIELD_PRICE]
            # save currency record in the database and get the record id
            query = currency.insert().values(
                currency_id=create_random_id(),
                iso_currency=iso_currency,
                last_rate=last_rate,
                symbol=symbol,
                last_update=datetime.utcnow(),
            )
            currency_id = await database.execute(query)
        else:
            # if currency exists just save the id (needed for stock creation)
            currency_id = currency_record.currency_id

        # create stock record
        query = stocks.insert().values(
            stock_id=create_random_id(),
            currency_id=currency_id,
            isin=new_stock.isin,
            market=stock_info[YAHOO_FIELD_MARKET],
            symbol=stock_symbol,
            last_price=stock_info[YAHOO_FIELD_PRICE],
            last_update=datetime.utcnow(),
        )
        stock_id = await database.execute(query)
    else:
        # if stock record exists already just save the id
        stock_id = stock_record.stock_id

    # create response dict from body model and add stock id to it
    stock = new_stock.dict()
    stock["stock_id"] = stock_id

    return stock


@router.delete("/")
@database.transaction()
async def delete_stock(
    stock_to_delete: StockToDelete,
    _: User = Depends(get_current_user),
):
    query = stock_transactions.select().where(
        stock_transactions.c.stock_id == stock_to_delete.stock_id
    )
    record = await database.fetch_one(query)
    if record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock_id {stock_to_delete.stock_id} is actually in use",
        )
    query = stocks.delete().where(stocks.c.stock_id == stock_to_delete.stock_id)
    await database.execute(query)


@router.put(
    "/transaction/{owner_id}",
    response_model=StockTransaction,
)
@database.transaction()
async def create_stock_transaction(
    owner_id: int,
    new_stock_transaction: NewStockTransaction,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
    query = stocks.select().where(stocks.c.stock_id == new_stock_transaction.stock_id)
    record = await database.fetch_one(
        query
    )  # Fab: fetch_one takes only the first reccord
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock id {new_stock_transaction.stock_id} doesn't exist",
        )
    # added validation, first transaction has to be a buy
    # and when you have a sell the quantity must be less than the total held
    # (query the stock_transactions table filtering it by owner_id and stock_id
    # than if the list is empty just check that the request body transaction_type is buy
    # if it is not empty and the transaction_type is sell sum the transactions
    # quantities, taking in account sells and buys,
    # and check that the sum is equal or greater than request body quantity)
    query = (
        stock_transactions.select()
        .where(stock_transactions.c.owner_id == owner_id)
        .where(stock_transactions.c.stock_id == new_stock_transaction.stock_id)
    )
    # fetch_all returns a list of records that match the query
    records = await database.fetch_all(query)
    validate_stock_transaction(records, new_stock_transaction)
    query = stock_transactions.insert().values(
        stock_transaction_id=create_random_id(),
        stock_id=new_stock_transaction.stock_id,
        price=new_stock_transaction.price,
        quantity=new_stock_transaction.quantity,
        tax=new_stock_transaction.tax,
        commission=new_stock_transaction.commission,
        transaction_type=new_stock_transaction.transaction_type,
        date=new_stock_transaction.date,
        owner_id=owner_id,
    )
    stock_transaction_id = await database.execute(query)
    stock_transaction = new_stock_transaction.dict()
    stock_transaction["stock_transaction_id"] = stock_transaction_id
    return stock_transaction


@router.get(
    "/transaction/{owner_id}/history/{stock_id}",
    response_model=StockTransactionHistory,
)
async def get_stock_transaction_history(
    owner_id: int,
    stock_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)

    query = (
        stock_transactions.select()
        .where(stock_transactions.c.owner_id == owner_id)
        .where(stock_transactions.c.stock_id == stock_id)
    )
    # Fab: fetch_all returns a list of records that match the query
    records = await database.fetch_all(query)
    history = {"transactions": []}
    for transaction in records:
        history["transactions"].append(
            {
                "price": transaction.price,
                "quantity": transaction.quantity,
                "tax": transaction.tax,
                "commission": transaction.commission,
                "date": transaction.date,
                "transaction_type": transaction.transaction_type,
                "stock_id": stock_id,
                "stock_transaction_id": transaction.stock_transaction_id,
            }
        )
    return history


@router.get(
    "/traded/{owner_id}",
    response_model=TradedStocks,
)
async def get_traded_stocks(
    owner_id: int,
    user: User = Depends(get_current_user),
):

    owner_data = await get_owner(user.user_id, owner_id)

    query = (
        select(
            [
                stocks.c.stock_id,
                currency.c.iso_currency,
                currency.c.last_rate,
                stocks.c.isin,
                stocks.c.symbol,
                stocks.c.last_price,
                stocks.c.market,
                stock_transactions.c.transaction_type,
                stock_transactions.c.quantity,
                stock_transactions.c.price,
                stock_transactions.c.commission,
                stock_transactions.c.date,
                stock_transactions.c.tax,
            ]
        )
        .select_from(
            stock_transactions.join(
                stocks, stock_transactions.c.stock_id == stocks.c.stock_id
            ).join(currency, currency.c.currency_id == stocks.c.currency_id)
        )
        .where(stock_transactions.c.owner_id == owner_id)
        .order_by(stocks.c.stock_id)
    )
    records = await database.fetch_all(query)
    traded_stocks = {"stocks": []}
    previous_stock_id = None
    if records:
        previous_stock_id = records[0][0]
        records.append([None])  # this triggers the addition of the last stock
    current_transactions = []
    current_buy_tax = 0
    current_quantity = 0
    for i, record in enumerate(records):
        if previous_stock_id != record[0]:
            previous_stock_id = record[0]
            previous_record = records[i - 1]
            fiscal_price = calculate_fiscal_price(current_transactions)
            commission = calculate_commission(
                owner_data[1],
                previous_record[6],
                previous_record[5],
                current_quantity,
            )
            sell_tax = calculate_sell_tax(
                previous_record[6],
                fiscal_price,
                previous_record[5],
                current_quantity,  # total qty of all transactions of one stock_id
            )
            profit_and_loss = calculate_profit_and_loss(
                fiscal_price,
                previous_record[5],
                current_buy_tax,
                sell_tax,
                commission,
                current_quantity,
            )
            # here we are resetting the tax and qty to zero
            # and transactions to empty list for the next group of transactions
            current_buy_tax = 0
            current_quantity = 0
            current_transactions = []

            traded_stocks["stocks"].append(
                {
                    "stock_id": previous_record[0],
                    "currency": previous_record[1],
                    "last_rate": previous_record[2],
                    "isin": previous_record[3],
                    "symbol": previous_record[4],
                    "last_price": previous_record[5],
                    "market": previous_record[6],
                    "fiscal_price": fiscal_price,
                    "profit_and_loss": profit_and_loss,
                }
            )
        if i != len(records) - 1:
            current_transactions.append(
                Transaction(
                    transaction_type=record[7],
                    quantity=record[8],
                    price=record[9],
                    commission=record[10],
                    date=record[11],
                )
            )
            if record[7] == TransactionType.buy.value:
                current_buy_tax += record[12]  # buy type will add tax
                current_quantity += record[8]  # buy type will add qty
            else:
                current_quantity -= record[8]  # sell type will reduce qty
    return traded_stocks


@router.delete("/transaction")
@database.transaction()
async def delete_stock_transaction(
    transaction: StockTransactionToDelete, user: User = Depends(get_current_user)
):
    query = stock_transactions.select().where(
        stock_transactions.c.stock_transaction_id == transaction.stock_transaction_id
    )
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock transaction {transaction.stock_transaction_id} doesn't exist",
        )
    await get_owner(user.user_id, record.owner_id)
    query = stock_transactions.delete().where(
        stock_transactions.c.stock_transaction_id == transaction.stock_transaction_id
    )
    await database.execute(query)

    # implemented this endpoint: first create a select query
    # and fetch (database.fetch_one) the transaction
    # if the transaction doesn't exist raise HttpException with code 422,
    # call get_owner that checks if the transaction belongs to the user
    # finally create the delete query (similiar to select but with delete) and than
    # execute it (example: await database.execute(query))
    # there is no need to return anything just ending the function without
    # exceptions returns a 200 code (success)


@router.patch("/transaction")
@database.transaction()
async def update_stock_transaction(
    transaction: StockTransactionToUpdate, user: User = Depends(get_current_user)
):
    query = stock_transactions.select().where(
        stock_transactions.c.stock_transaction_id == transaction.stock_transaction_id
    )
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock transaction {transaction.stock_transaction_id} doesn't exist",
        )
    await get_owner(user.user_id, record.owner_id)
    transaction_dict = transaction.dict()
    values = {}
    for key in transaction_dict:
        if transaction_dict[key] is not None and key != "stock_transaction_id":
            values[key] = transaction_dict[key]
    if not values:
        return
    query = (
        stock_transactions.update()
        .where(
            stock_transactions.c.stock_transaction_id
            == transaction.stock_transaction_id
        )
        .values(**values)
    )
    await database.execute(query)
