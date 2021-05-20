import sqlalchemy

DATABASE_URL = "sqlite:///./santaka.db"

metadata = sqlalchemy.MetaData()


users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("user_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlite_autoincrement=True,
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
    sqlite_autoincrement=True,
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
    sqlite_autoincrement=True,
)

currency = sqlalchemy.Table(
    "currency",
    metadata,
    sqlalchemy.Column("currency_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("iso_currency", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("last_rate", sqlalchemy.DECIMAL, nullable=False),
    sqlite_autoincrement=True,
)

stocks = sqlalchemy.Table(
    "stocks",
    metadata,
    sqlalchemy.Column("stock_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("isin", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("market", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("symbol", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("last_price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column(
        "currency_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("currency.currency_id"),
        nullable=False,
    ),
    sqlite_autoincrement=True,
)

stock_transactions = sqlalchemy.Table(
    "stock_transactions",
    metadata,
    sqlalchemy.Column("stock_transactions_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "account_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("accounts.account_id"),
        nullable=False,
    ),
    sqlalchemy.Column(
        "stock_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("stocks.stock_id"),
        nullable=False,
    ),
    sqlalchemy.Column("price", sqlalchemy.DECIMAL, nullable=False),
    sqlalchemy.Column("quantity", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("tax", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("commission", sqlalchemy.DECIMAL, default=0),
    sqlalchemy.Column("date", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("transaction_type", sqlalchemy.String, nullable=False),
    sqlite_autoincrement=True,
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
    sqlite_autoincrement=True,
)

bond_transactions = sqlalchemy.Table(
    "bond_transactions",
    metadata,
    sqlalchemy.Column("bond_transactions_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "account_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("accounts.account_id"),
        nullable=False,
    ),
    sqlalchemy.Column(
        "bond_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("bonds.bond_id"),
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
    sqlite_autoincrement=True,
)


engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)