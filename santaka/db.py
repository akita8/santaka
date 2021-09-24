from random import randint
from os import environ

import sqlalchemy
from databases import Database

DATABASE_URL = environ.get("DATABASE_URL", "sqlite:///./santaka.db")
TEST_DATABASE_URL = "sqlite:///:memory:"

metadata = sqlalchemy.MetaData()


users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("user_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("base_currency", sqlalchemy.String, nullable=False),
)

accounts = sqlalchemy.Table(
    "accounts",
    metadata,
    sqlalchemy.Column("account_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "user_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("users.user_id"),
        nullable=False,
    ),
    sqlalchemy.Column("bank", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("account_number", sqlalchemy.String, nullable=False),
)

owners = sqlalchemy.Table(
    "owners",
    metadata,
    sqlalchemy.Column("owner_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "account_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("accounts.account_id"),
        nullable=False,
    ),
    sqlalchemy.Column("fullname", sqlalchemy.String, nullable=False),
)

currency = sqlalchemy.Table(
    "currency",
    metadata,
    sqlalchemy.Column("currency_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("iso_currency", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("last_rate", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("symbol", sqlalchemy.String, nullable=True, unique=True),
    sqlalchemy.Column("last_update", sqlalchemy.DateTime, nullable=False),
)

stocks = sqlalchemy.Table(
    "stocks",
    metadata,
    sqlalchemy.Column("stock_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("market", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("symbol", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column(
        "financial_currency",
        sqlalchemy.String,
        nullable=False,
    ),
    sqlalchemy.Column(
        "short_name",
        sqlalchemy.String,
        nullable=False,
    ),
    sqlalchemy.Column("last_price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("last_update", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(
        "currency_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("currency.currency_id"),
        nullable=False,
    ),
)

stock_transactions = sqlalchemy.Table(
    "stock_transactions",
    metadata,
    sqlalchemy.Column("stock_transaction_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "stock_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("stocks.stock_id"),
        nullable=False,
    ),
    sqlalchemy.Column(
        "owner_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("owners.owner_id"),
        nullable=False,
    ),
    sqlalchemy.Column("price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("quantity", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("tax", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("commission", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("date", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("transaction_type", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("transaction_note", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("transaction_ex_rate", sqlalchemy.DECIMAL, nullable=False),
)
stock_alerts = sqlalchemy.Table(
    "stock_alerts",
    metadata,
    sqlalchemy.Column("stock_alert_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "stock_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("stocks.stock_id"),
        nullable=False,
    ),
    sqlalchemy.Column(
        "owner_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("owners.owner_id"),
        nullable=False,
    ),
    sqlalchemy.Column("dividend_date", sqlalchemy.DateTime, nullable=True),
    sqlalchemy.Column("lower_limit_price", sqlalchemy.DECIMAL, nullable=True),
    sqlalchemy.Column("upper_limit_price", sqlalchemy.DECIMAL, nullable=True),
    sqlalchemy.Column("fiscal_price_lower_than", sqlalchemy.BOOLEAN, nullable=True),
    sqlalchemy.Column("fiscal_price_greater_than", sqlalchemy.BOOLEAN, nullable=True),
    sqlalchemy.Column("profit_and_loss_lower_limit", sqlalchemy.DECIMAL, nullable=True),
    sqlalchemy.Column("profit_and_loss_upper_limit", sqlalchemy.DECIMAL, nullable=True),
)

bonds = sqlalchemy.Table(
    "bonds",
    metadata,
    sqlalchemy.Column("bond_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("isin", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("market", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("last_price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column(
        "currency_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("currency.currency_id"),
        nullable=False,
    ),
    sqlalchemy.Column("expiry_date", sqlalchemy.Time, nullable=False),
    sqlalchemy.Column("first_coupon_date", sqlalchemy.Time, nullable=False),
    sqlalchemy.Column("yearly_coupon_percent", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("coupon_frequency", sqlalchemy.Integer, nullable=False),
)

bond_transactions = sqlalchemy.Table(
    "bond_transactions",
    metadata,
    sqlalchemy.Column("bond_transactions_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "bond_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("bonds.bond_id"),
        nullable=False,
    ),
    sqlalchemy.Column(
        "owner_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("owners.owner_id"),
        nullable=False,
    ),
    sqlalchemy.Column("price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("quantity", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("tax", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("coupon_tax", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("commission", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column(
        "issue_discount", sqlalchemy.DECIMAL, default=0
    ),  # disaggio di emissione
    sqlalchemy.Column("date", sqlalchemy.Time, nullable=False),
    sqlalchemy.Column("transaction_type", sqlalchemy.String, nullable=False),
)


engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

if "PYTEST_CURRENT_TEST" in environ:
    database = Database(TEST_DATABASE_URL, force_rollback=True)
else:
    database = Database(DATABASE_URL)


def create_random_id(length: int = 15):
    return randint(10 ** (length - 1), (10 ** (length) - 1))
