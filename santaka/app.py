from datetime import datetime, timedelta
from os import environ

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from databases import Database
from sqlalchemy.sql import select
from jose import JWTError, jwt
from passlib.context import CryptContext

from santaka.db import (
    DATABASE_URL,
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
    User,
    NewStockTransaction,
    StockTransaction,
)
from santaka.utils import get_yahoo_quote, YahooError


# the default value for SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES are only for dev,
# export valid ones in prod
SECRET_KEY = environ.get("SECRET_KEY", "secret")
ACCESS_TOKEN_EXPIRE_MINUTES = environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 24 * 60)
ALGORITHM = "HS256"
DEFAULT_CURRENCY = "EUR"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
database = Database(DATABASE_URL)
app = FastAPI()


def verify_password(plain_password, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(username, password: str):
    hashed_password = pwd_context.hash(password)
    query = users.insert().values(username=username, password=hashed_password)
    user_id = await database.execute(query)
    print(f"created user {username} with {user_id} id")


async def get_user(username: str):
    query = users.select().where(users.c.username == username)
    record = await database.fetch_one(query)
    if record is None:
        return None, None
    return User(username=username, user_id=record.user_id), record.password


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
        account_number=new_account.account_number,
        bank=new_account.bank,
        user_id=user.user_id,
    )
    account_id = await database.execute(query)
    for owner in new_account.owners:
        query = owners.insert().values(account_id=account_id, fullname=owner)
        await database.execute(query)
    account = new_account.dict()
    account["account_id"] = account_id
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
            account_models.append(
                {
                    "bank": record[0],
                    "account_number": record[2],
                    "account_id": record[1],
                    "owners": [record[3]],
                }
            )
        else:
            account_models[-1]["owners"].append(record[3])
        previous_account_id = record[1]

    return {"accounts": account_models}


@app.post("/stock", response_model=Stock)
async def create_stock(new_stock: NewStock, _: User = Depends(get_current_user)):
    query = currency.select().where(currency.c.iso_currency == new_stock.currency)
    currency_record = await database.fetch_one(query)
    stock_record = None
    if currency_record is None:
        if new_stock.currency == DEFAULT_CURRENCY:
            last_rate = 1
        else:
            symbol = f"{DEFAULT_CURRENCY}{new_stock.currency}=X"
            try:
                quotes = await get_yahoo_quote([symbol])
            except YahooError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Call to provider unsuccessful",
                )
            if symbol not in quotes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Symbol {symbol} doesn't exist",
                )
            last_rate = quotes[symbol]
        query = currency.insert().values(
            iso_currency=new_stock.currency, last_rate=last_rate
        )
        currency_id = await database.execute(query)
    else:
        currency_id = currency_record.currency_id
        query = (
            stocks.select()
            .where(stocks.c.isin == new_stock.isin)
            .where(stocks.c.market == new_stock.market)
            .where(stocks.c.symbol == new_stock.symbol)
            .where(stocks.c.currency_id == currency_id)
        )
        stock_record = await database.fetch_one(query)
    if stock_record is None:
        last_price = 0
        query = stocks.insert().values(
            currency_id=currency_id,
            isin=new_stock.isin,
            market=new_stock.market,
            symbol=new_stock.symbol,
            last_price=last_price,
        )
        stock_id = await database.execute(query)
    else:
        stock_id = stock_record.stock_id
        last_price = stock_record.last_price
    stock = new_stock.dict()
    stock["last_price"] = last_price
    stock["stock_id"] = stock_id
    return stock


@app.post("/stock/{stock_id}/transaction", response_model=StockTransaction)
async def create_stock_transaction(
    stock_id: int,
    new_stock_transaction: NewStockTransaction,
    user: User = Depends(get_current_user),
):
    query = stocks.select().where(stocks.c.stock_id == stock_id)
    record = await database.fetch_one(query)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock id {stock_id} doesn't exist",
        )
    query = (
        accounts.select()
        .where(accounts.c.account_id == new_stock_transaction.account_id)
        .where(accounts.c.user_id == user.user_id)
    )
    record = await database.fetch_one(query)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account_id {new_stock_transaction.account_id} doesn't exist",
        )
    query = stock_transactions.insert().values(
        stock_id=stock_id,
        account_id=new_stock_transaction.account_id,
        price=new_stock_transaction.price,
        quantity=new_stock_transaction.quantity,
        tax=new_stock_transaction.tax,
        commission=new_stock_transaction.commission,
        transaction_type=new_stock_transaction.transaction_type,
        date=new_stock_transaction.date,
    )
    stock_transaction_id = await database.execute(query)
    stock_transaction = new_stock_transaction.dict()
    stock_transaction["stock_transaction_id"] = stock_transaction_id
    return stock_transaction
