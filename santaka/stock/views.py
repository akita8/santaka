from datetime import datetime

from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy.sql import select

from santaka.db import (
    database,
    stocks,
    currency,
    stock_transactions,
    create_random_id,
    stock_alerts,
    users,
    accounts,
    owners,
)
from santaka.user import User, get_current_user
from santaka.account.utils import get_owner
from santaka.stock.models import (
    NewStock,
    NewStockAlert,
    DetailedStock,
    StockAlert,
    StockAlerts,
    StockAlertToDelete,
    StockAlertToUpdate,
    StockToDelete,
    StockToUpdate,
    NewStockTransaction,
    StockTransaction,
    StockTransactionHistory,
    StockTransactionsToMove,
    Stocks,
    TradedStock,
    TradedStocks,
    StockTransactionToDelete,
    StockTransactionToUpdate,
    Currency,
    UpdatedStocks,
    UpdatedStock,
    TransactionType,
    Currencies,
)
from santaka.stock.utils import (
    YAHOO_FIELD_FINANCIAL_CURRENCY,
    YAHOO_FIELD_LONG_NAME,
    call_yahoo_from_view,
    get_alert_or_raise,
    get_stock_records,
    get_yahoo_quote,
    validate_stock_transaction,
    prepare_traded_stocks,
    get_transaction_records,
    check_stock_alerts,
    YAHOO_FIELD_CURRENCY,
    YAHOO_FIELD_MARKET,
    YAHOO_FIELD_PRICE,
    YAHOO_FIELD_NAME,
)
from santaka.stock.analytics import calculate_stock_totals

router = APIRouter(prefix="/stock", tags=["stock"])


@router.put("/", response_model=DetailedStock)
@database.transaction()
async def create_stock(new_stock: NewStock, user: User = Depends(get_current_user)):
    # query the database to check if stock already exists
    stock_symbol = new_stock.symbol.upper()
    stock_records = await get_stock_records(stock_symbol)

    # create response dict from body model
    stock = new_stock.dict()

    if not stock_records:
        # stock not found in the database, calling yahoo to get stock info
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
        name = stock_info.get(YAHOO_FIELD_NAME, stock_info[YAHOO_FIELD_LONG_NAME])
        # create stock record
        query = stocks.insert().values(
            stock_id=create_random_id(),
            short_name=name,
            currency_id=currency_id,
            market=stock_info[YAHOO_FIELD_MARKET],
            symbol=stock_symbol,
            last_price=stock_info[YAHOO_FIELD_PRICE],
            last_update=datetime.utcnow(),
            financial_currency=stock_info.get(YAHOO_FIELD_FINANCIAL_CURRENCY),
        )
        stock_id = await database.execute(query)
        stock["short_name"] = name
        stock["iso_currency"] = iso_currency
        stock["currency_id"] = currency_id
        stock["market"] = stock_info[YAHOO_FIELD_MARKET]
        stock["symbol"] = stock_symbol
        stock["last_price"] = stock_info[YAHOO_FIELD_PRICE]
    else:
        # if stock record exists already
        stock_record = stock_records[0]
        stock_id = stock_record[3]
        stock["short_name"] = stock_record[1]
        stock["iso_currency"] = stock_record[6]
        stock["currency_id"] = stock_record[5]
        stock["market"] = stock_record[4]
        stock["symbol"] = stock_symbol
        stock["last_price"] = stock_record[0]
    stock["stock_id"] = stock_id

    return stock


@router.get("/currency/", response_model=Currencies)
async def get_currencies(_: User = Depends(get_current_user)):
    query = currency.select()
    records = await database.fetch_all(query)
    currencies = []
    for record in records:
        currencies.append(
            {"iso_currency": record.iso_currency, "last_rate": record.last_rate}
        )
    return {"currencies": currencies}


@router.post("/currency/{currency_id}", response_model=Currency)
@database.transaction()
async def update_currency(currency_id: int, user: User = Depends(get_current_user)):
    query = currency.select().where(currency.c.currency_id == currency_id)
    currency_record = await database.fetch_one(query)
    if currency_record.iso_currency == user.base_currency:
        return {
            "iso_currency": currency_record.iso_currency,
            "last_rate": 1,
        }
    currency_info = await call_yahoo_from_view(currency_record.symbol)
    query = currency.update()
    query = query.values(last_rate=currency_info[YAHOO_FIELD_PRICE])
    query = query.where(currency.c.symbol == currency_record.symbol)
    await database.execute(query)
    return {
        "iso_currency": currency_record.iso_currency,
        "last_rate": currency_info[YAHOO_FIELD_PRICE],
    }


@router.post("/currency/", response_model=Currencies)
async def update_currencies(user: User = Depends(get_current_user)):
    query = currency.select().where(currency.c.iso_currency != user.base_currency)
    symbol_records = await database.fetch_all(query)
    symbols = []
    for record in symbol_records:
        symbols.append(record.symbol)
    currencies_to_update = await get_yahoo_quote(symbols)
    updated_currencies = []
    for symbol in currencies_to_update:
        last_rate = currencies_to_update[symbol][YAHOO_FIELD_PRICE]
        query = (
            currency.update()
            .values(last_rate=last_rate)
            .where(currency.c.symbol == symbol)
        )
        await database.execute(query)
        updated_currencies.append(
            {
                "iso_currency": currencies_to_update[symbol][YAHOO_FIELD_CURRENCY],
                "last_rate": last_rate,
            }
        )
    return {"currencies": updated_currencies}


@router.post("/{stock_id}", response_model=UpdatedStock)
@database.transaction()
async def update_stock_quote(stock_id: int, user: User = Depends(get_current_user)):
    query = stocks.select().where(stocks.c.stock_id == stock_id)
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock{stocks.symbol} doesn't exist",
        )
    quote = await call_yahoo_from_view(record.symbol)
    query = stocks.update()
    query = query.values(
        last_price=quote[YAHOO_FIELD_PRICE],
        last_update=datetime.utcnow(),
    )
    query = query.where(stocks.c.symbol == record.symbol)
    await database.execute(query)
    return {"symbol": record.symbol, "last_price": quote[YAHOO_FIELD_PRICE]}


@router.post("/", response_model=UpdatedStocks)
@database.transaction()
async def update_stocks(user: User = Depends(get_current_user)):
    query = select([stocks.c.symbol])
    join_clause = users.join(accounts, accounts.c.user_id == users.c.user_id)
    join_clause = join_clause.join(owners, owners.c.account_id == accounts.c.account_id)
    join_clause = join_clause.join(
        stock_transactions, stock_transactions.c.owner_id == owners.c.owner_id
    )
    join_clause = join_clause.join(
        stocks, stocks.c.stock_id == stock_transactions.c.stock_id
    )
    query = query.select_from(join_clause)
    query = query.where(users.c.user_id == user.user_id)
    query = query.distinct()

    symbol_records = await database.fetch_all(query)
    symbols = []
    for record in symbol_records:
        symbols.append(record[0])
    quotes = await get_yahoo_quote(symbols)
    updated_stocks = []
    for symbol in quotes:
        query = stocks.update()
        query = query.values(
            last_price=quotes[symbol][YAHOO_FIELD_PRICE],
            last_update=datetime.utcnow(),
        )
        query = query.where(stocks.c.symbol == symbol)
        await database.execute(query)
        updated_stocks.append(
            {"symbol": symbol, "last_price": quotes[symbol][YAHOO_FIELD_PRICE]}
        )
    return {"stocks": updated_stocks}


@router.get("/", response_model=Stocks)
async def get_stocks(_: User = Depends(get_current_user)):
    records = await get_stock_records()
    stocks_entered = {"stocks": []}
    for record in records:
        stocks_entered["stocks"].append(
            {
                "last_price": record[0],
                "short_name": record[1],
                "symbol": record[2],
                "stock_id": record[3],
                "market": record[4],
                "currency_id": record[5],
                "iso_currency": record[6],
            }
        )
    return stocks_entered


@router.patch("/")
@database.transaction()
async def update_stock(
    stock_to_update: StockToUpdate,
    _: User = Depends(get_current_user),
):
    query = stocks.select().where(stocks.c.stock_id == stock_to_update.stock_id)
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock{stocks.stock_id} doesn't exist",
        )
    stock_dict = stock_to_update.dict()
    values = {}
    for key in stock_dict:
        if stock_dict[key] is not None and key != "stock_id":
            values[key] = stock_dict[key]
    if not values:
        return
    query = (
        stocks.update()
        .where(stocks.c.stock_id == stock_to_update.stock_id)
        .values(**values)
    )
    await database.execute(query)


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
    "/transaction/{owner_id}/",
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
    record = await database.fetch_one(query)
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
    exchange_rate = 1
    if new_stock_transaction.transaction_ex_rate is not None:
        exchange_rate = new_stock_transaction.transaction_ex_rate
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
        transaction_note=new_stock_transaction.transaction_note,
        transaction_ex_rate=exchange_rate,
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
                "transaction_note": transaction.transaction_note,
                "transaction_ex_rate": transaction.transaction_ex_rate,
            }
        )
    return history


@router.get("/traded/{owner_id}/{stock_id}/", response_model=TradedStock)
async def get_traded_stock_summary(
    owner_id: int, stock_id: int, user: User = Depends(get_current_user)
):
    await get_owner(user.user_id, owner_id)
    records = await get_transaction_records([owner_id], stock_id)
    if len(records) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock id {stock_id} doesn't exist for this owner",
        )
    traded_stocks = prepare_traded_stocks(records)
    return traded_stocks[0]


@router.get(
    "/traded/{owner_id}/",
    response_model=TradedStocks,
)
async def get_traded_stocks(
    owner_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
    records = await get_transaction_records([owner_id])
    traded_stocks = prepare_traded_stocks(records)
    (
        invested_converted,
        profit_and_loss_converted,
        current_ctv_converted,
        current_status_converted,
    ) = calculate_stock_totals(traded_stocks)
    return {
        "stocks": traded_stocks,
        "invested_converted": invested_converted,
        "profit_and_loss_converted": profit_and_loss_converted,
        "current_ctv_converted": current_ctv_converted,
        "current_status_converted": current_status_converted,
    }


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


@router.post("/{stock_id}/move/{owner_id}", response_model=StockTransactionsToMove)
@database.transaction()
async def move_stock_transaction(
    stock_transaction_to_move: StockTransactionsToMove,
    stock_id: int,
    owner_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
    query = stock_transactions.select().where(
        stock_transactions.c.stock_transaction_id.in_(
            stock_transaction_to_move.stock_transaction_ids
        )
    )
    records = await database.fetch_all(query)
    if records[0].transaction_type != TransactionType.buy.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"First transaction {records[0].stock_transaction_id} is not a BUY",
        )
    for record in records:
        if record.stock_id != stock_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Stock_id {record.stock_id} doesn't exist",
            )
    query = (
        stock_transactions.update()
        .values(owner_id=owner_id)
        .where(
            stock_transactions.c.stock_transaction_id.in_(
                stock_transaction_to_move.stock_transaction_ids
            )
        )
    )
    await database.execute(query)
    return stock_transaction_to_move


# TODO add get currencies view


@router.put("/alert", response_model=StockAlert)
@database.transaction()
async def create_stock_alert(
    new_stock_alert: NewStockAlert,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, new_stock_alert.owner_id)
    if (
        new_stock_alert.lower_limit_price is None
        and new_stock_alert.upper_limit_price is None
        and new_stock_alert.dividend_date is None
        and new_stock_alert.fiscal_price_lower_than is None
        and new_stock_alert.fiscal_price_greater_than is None
        and new_stock_alert.profit_and_loss_greater_than is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be present",
        )

    query = (
        select([stock_alerts.c.stock_alert_id, stock_alerts.c.owner_id])
        .select_from(
            stocks.outerjoin(stock_alerts, stocks.c.stock_id == stock_alerts.c.stock_id)
        )
        .where(stocks.c.stock_id == new_stock_alert.stock_id)
    )
    records = await database.fetch_all(query)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock {new_stock_alert.stock_id} doesn't exist",
        )
    for record in records:
        if record[0] and record[1] == new_stock_alert.owner_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stock alert for stock "
                "{new_stock_alert.stock_id} already exists",
            )
    query = stock_alerts.insert().values(
        stock_alert_id=create_random_id(),
        stock_id=new_stock_alert.stock_id,
        owner_id=new_stock_alert.owner_id,
        lower_limit_price=new_stock_alert.lower_limit_price,
        upper_limit_price=new_stock_alert.upper_limit_price,
        dividend_date=new_stock_alert.dividend_date,
        fiscal_price_lower_than=new_stock_alert.fiscal_price_lower_than,
        fiscal_price_greater_than=new_stock_alert.fiscal_price_greater_than,
        profit_and_loss_lower_limit=new_stock_alert.profit_and_loss_lower_limit,
        profit_and_loss_upper_limit=new_stock_alert.profit_and_loss_upper_limit,
    )
    await database.execute(query)

    return await get_alert_or_raise(new_stock_alert.stock_id, new_stock_alert.owner_id)


@router.get("/alert/{owner_id}/", response_model=StockAlerts)
async def get_stock_alerts(
    owner_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
    alerts = {"alerts": await check_stock_alerts(owner_id=owner_id)}
    return alerts


@router.get("/alert/{owner_id}/{stock_id}/", response_model=StockAlert)
async def get_stock_alert(
    owner_id: int,
    stock_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
    return await get_alert_or_raise(stock_id, owner_id)


@router.delete("/alert")
@database.transaction()
async def delete_stock_alert(
    alert: StockAlertToDelete, _: User = Depends(get_current_user)
):
    query = stock_alerts.select().where(
        stock_alerts.c.stock_alert_id == alert.stock_alert_id
    )
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock alert {alert.stock_alert_id} doesn't exist",
        )
    query = stock_alerts.delete().where(
        stock_alerts.c.stock_alert_id == alert.stock_alert_id
    )
    await database.execute(query)


@router.patch("/alert")
@database.transaction()
async def update_stock_alert(
    alert: StockAlertToUpdate, _: User = Depends(get_current_user)
):
    query = stock_alerts.select().where(
        stock_alerts.c.stock_alert_id == alert.stock_alert_id
    )
    record = await database.fetch_one(query)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stock alert {alert.stock_alert_id} doesn't exist",
        )
    alert_dict = alert.dict()
    values = {}
    for key in alert_dict:
        if key != "stock_alert_id":
            values[key] = alert_dict[key]
    if values:
        query = (
            stock_alerts.update()
            .where(stock_alerts.c.stock_alert_id == alert.stock_alert_id)
            .values(**values)
        )
        await database.execute(query)
    return await get_alert_or_raise(record.stock_id, record.owner_id)


# TODO Refactor create stock dividing in in different views:
#      one to get stock (from db or yahoo), one to create stock,
#      one to get currency, one to create currencies
