from datetime import datetime, timedelta
from os import environ

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.sql import select
from jose import JWTError, jwt

from santaka.db import (
    database,
    accounts,
    owners,
    users,
    stocks,
    currency,
    stock_transactions,
)
from santaka.models import (
    NewAccount,
    Accounts,
    NewStock,
    Stock,
    Account,
    Token,
    TransactionType,
    User,
    NewStockTransaction,
    StockTransaction,
    StockTransactionHistory,
    TradedStocks,
)
from santaka.utils import (
    call_yahoo_from_view,
    YAHOO_FIELD_PRICE,
    YAHOO_FIELD_MARKET,
    YAHOO_FIELD_CURRENCY,
    get_user,
    get_owner,
    create_random_id,
    verify_password,
)


# the default value for SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES are only for dev,
# export valid ones in prod
SECRET_KEY = environ.get("SECRET_KEY", "secret")
ACCESS_TOKEN_EXPIRE_MINUTES = environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 24 * 60)
ALGORITHM = "HS256"
DEFAULT_CURRENCY = "EUR"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()


async def authenticate_user(username, password: str):
    user, hashed_password = await get_user(username)
    if not hashed_password:
        return None
    if not verify_password(password, hashed_password):
        return None
    return user


def create_access_token(username: str):
    to_encode = {"sub": username}
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user, _ = await get_user(username)
    if user is None:
        raise credentials_exception
    return user


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/token/refresh", response_model=Token)
def refresh_token(user: User = Depends(get_current_user)):
    access_token = create_access_token(user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(user: User = Depends(get_current_user)):
    return user


@app.post("/account", response_model=Account)
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


@app.get("/account", response_model=Accounts)
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
    records = await database.fetch_all(
        query
    )  # Fab: It takes all rows of the database based on previous query
    account_models = []
    previous_account_id = None
    for record in records:
        if record[1] != previous_account_id:
            account_models.append(
                {
                    "bank": record[0],
                    "account_number": record[2],
                    "account_id": record[1],
                    "owners": [{"name": record[3], "owner_id": record[4]}],
                }
            )
        else:
            account_models[-1]["owners"].append(
                {"name": record[3], "owner_id": record[4]}
            )
        previous_account_id = record[1]

    return {"accounts": account_models}


@app.put("/stock", response_model=Stock)
async def create_stock(new_stock: NewStock, _: User = Depends(get_current_user)):
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
            if iso_currency != DEFAULT_CURRENCY:
                # if stock currency is not the default one call yahoo
                #  to get currency info
                symbol = f"{DEFAULT_CURRENCY}{iso_currency}=X".upper()
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


@app.put(
    "/account/{owner_id}/transaction/stock",
    response_model=StockTransaction,
)
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
    # Fab: fetch_all returns a list of records that match the query
    records = await database.fetch_all(query)
    if not records and new_stock_transaction.transaction_type == TransactionType.sell:
        # fab:  >> if not << this sentence is the right way to identify an empty list
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="First transaction mast be a buy",
        )
    if records and new_stock_transaction.transaction_type == TransactionType.sell:
        quantity = 0
        for record in records:
            if record.transaction_type == TransactionType.sell.value:
                quantity -= record.quantity
            else:
                quantity += record.quantity
        if quantity < new_stock_transaction.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot sell more than {quantity} stocks",
            )
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


@app.get(
    "/account/{owner_id}/transaction/stock",
    response_model=TradedStocks,
)
async def get_traded_stocks(
    owner_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
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
            ]
        )
        .select_from(
            stock_transactions.join(
                stocks, stock_transactions.c.stock_id == stocks.c.stock_id
            ).join(currency, currency.c.currency_id == stocks.c.currency_id)
        )
        .where(stock_transactions.c.owner_id == owner_id)
    )
    records = await database.fetch_all(query)
    traded_stocks = {"stocks": []}
    for record in records:
        traded_stocks["stocks"].append(
            {
                "stock_id": record[0],
                "currency": record[1],
                "last_rate": record[2],
                "isin": record[3],
                "symbol": record[4],
                "last_price": record[5],
                "market": record[6],
            }
        )
    return traded_stocks


@app.get(
    "/account/{owner_id}/transaction/stock/{stock_id}",
    response_model=StockTransactionHistory,
)
async def get_stock_transaction_history(
    owner_id: int,
    stock_id: int,
    user: User = Depends(get_current_user),
):
    await get_owner(user.user_id, owner_id)
