from fastapi import FastAPI
from uvicorn import run

from santaka.db import database
from santaka.user import router as user_router
from santaka.account import router as account_router
from santaka.stock.views import router as stock_router

app = FastAPI()

app.include_router(user_router)
app.include_router(account_router)
app.include_router(stock_router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
