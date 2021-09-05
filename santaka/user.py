from os import environ
from datetime import datetime, timedelta
from typing import Tuple

from fastapi import status, HTTPException, Depends, APIRouter
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt

from santaka.db import database, users, create_random_id

# the default value for SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES are only for dev,
# export valid ones in prod
SECRET_KEY = environ.get("SECRET_KEY", "secret")
ACCESS_TOKEN_EXPIRE_MINUTES = environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 24 * 60)
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/user", tags=["user"])


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    user_id: int
    base_currency: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@database.transaction()
async def create_user(username: str, password: str, base_currency: str):
    hashed_password = pwd_context.hash(password)
    query = users.insert().values(
        user_id=create_random_id(),
        username=username,
        password=hashed_password,
        base_currency=base_currency,
    )
    user_id = await database.execute(query)
    print(f"created user {username} with {user_id} id")


async def get_user(username: str) -> Tuple[User, str]:
    query = users.select().where(users.c.username == username)
    record = await database.fetch_one(query)
    if record is None:
        return None, None
    return (
        User(
            username=username,
            user_id=record.user_id,
            base_currency=record.base_currency,
        ),
        record.password,
    )


async def authenticate_user(username: str, password: str) -> User:
    user, hashed_password = await get_user(username)
    if not hashed_password:
        return None
    if not verify_password(password, hashed_password):
        return None
    return user


def create_access_token(username: str) -> str:
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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
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


@router.post("/token/", response_model=Token)
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


@router.get("/token/refresh/", response_model=Token)
def refresh_token(user: User = Depends(get_current_user)):
    access_token = create_access_token(user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me/", response_model=User)
async def read_users_me(user: User = Depends(get_current_user)):
    return user
