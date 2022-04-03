from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run

from santaka.db import database
from santaka.user import router as user_router
from santaka.account.views import router as account_router
from santaka.stock.views import router as stock_router

# from santaka.bond.views import router as bond_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(account_router)
app.include_router(stock_router)
# app.include_router(bond_router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
