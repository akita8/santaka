from decimal import Decimal
from typing import List, Optional, Tuple

from santaka.stock.models import (
    TradedStock,
    Transaction,
    TransactionType,
    SplitEvent,
)


def calculate_profit_and_loss(
    fiscal_price: Decimal,
    last_price: Decimal,
    sell_tax: Decimal,
    sell_commission: Decimal,
    quantity: int,
) -> Decimal:
    invested = quantity * fiscal_price
    sold = quantity * last_price - sell_commission - sell_tax
    return sold - invested


def calculate_invested(
    fiscal_price: Decimal, fiscal_price_converted: Decimal, quantity: int
) -> Tuple[Decimal, Decimal]:
    invested = quantity * fiscal_price
    invested_converted = quantity * fiscal_price_converted
    return invested, invested_converted


def calculate_ctvs(
    last_price: Decimal, last_rate: Decimal, quantity: int
) -> Tuple[Decimal, Decimal]:
    current_ctv = quantity * last_price
    current_ctv_converted = current_ctv / last_rate
    return current_ctv, current_ctv_converted


def calculate_stock_totals(
    traded_stocks: List[TradedStock],
) -> Tuple[Decimal, Decimal, Decimal]:
    invested_converted = 0
    profit_and_loss_converted = 0
    current_ctv_converted = 0
    for stock in traded_stocks:
        invested_converted += stock["invested_converted"]
        profit_and_loss_converted += stock["profit_and_loss_converted"]
        current_ctv_converted += stock["current_ctv_converted"]

    return invested_converted, profit_and_loss_converted, current_ctv_converted


def calculate_fiscal_price(
    transactions: List[Transaction], split_events: Optional[List[SplitEvent]] = None
) -> Tuple[Decimal, Decimal]:
    invested = 0
    invested_converted = 0
    quantity = 0
    split_index = 0
    for transaction in transactions:
        if (
            split_events
            and split_index < len(split_events)
            and transaction.date > split_events[split_index].date
        ):
            quantity = split_events[split_index].factor * quantity
            split_index += 1
        if transaction.transaction_type == TransactionType.buy:
            quantity = quantity + transaction.quantity
            invested = invested + (
                transaction.price * transaction.quantity + transaction.commission
            )
            invested_converted = (
                invested_converted
                + (transaction.price * transaction.quantity + transaction.commission)
                / transaction.transaction_ex_rate
            )
        elif transaction.transaction_type == TransactionType.sell:
            new_quantity = quantity - transaction.quantity
            invested = (invested / quantity) * new_quantity
            invested_converted = (invested_converted / quantity) * new_quantity
            quantity = new_quantity
    while split_events and split_index < len(split_events):
        quantity = split_events[split_index].factor * quantity
        split_index += 1
    return invested / quantity, invested_converted / quantity


def calculate_status(
    transactions: List[Transaction], last_price: Decimal, last_rate: Decimal
) -> Tuple[Decimal, Decimal]:
    bought = 0
    bought_converted = 0
    sold = 0
    sold_converted = 0
    dividends = 0
    dividends_converted = 0
    current_quantity = 0
    for transaction in transactions:
        if transaction.transaction_type == TransactionType.buy:
            current_quantity += transaction.quantity
            bought += (
                transaction.price * transaction.quantity
                + transaction.commission
                + transaction.tax
            )
            bought_converted += (
                transaction.price * transaction.quantity
                + transaction.commission
                + transaction.tax
            ) / transaction.transaction_ex_rate
        if transaction.transaction_type == TransactionType.sell:
            current_quantity -= transaction.quantity
            sold += (
                transaction.price * transaction.quantity
                - transaction.commission
                - transaction.tax
            )
            sold_converted += (
                transaction.price * transaction.quantity
                - transaction.commission
                - transaction.tax
            ) / transaction.transaction_ex_rate
        elif transaction.transaction_type == TransactionType.dividend:
            dividends += transaction.price * current_quantity - transaction.tax
            dividends_converted += (
                transaction.price * current_quantity - transaction.tax
            ) / transaction.transaction_ex_rate
    current_status = sold - bought + dividends + (last_price * current_quantity)
    current_status_converted = (
        sold_converted
        - bought_converted
        + dividends_converted
        + (last_price * current_quantity / last_rate)
    )

    return current_status, current_status_converted


if __name__ == "__main__":
    import datetime

    print(
        calculate_status(
            [
                Transaction(
                    price=335.488,  # LMT Che Banca
                    quantity=2,
                    transaction_type=TransactionType.buy,
                    date=datetime.datetime(2021, 1, 12),
                    transaction_ex_rate=1.215001,
                    tax=0,
                    commission=14.734,
                ),
                # Transaction(
                #     price=289.975,
                #     quantity=3,
                #     transaction_type=TransactionType.buy,
                #     date=datetime.datetime(2020, 10, 28),
                #     transaction_ex_rate=1.11042,
                #     tax=0,
                #     commission=3.95,
                # ),
                # Transaction(
                #     price=300.0144,
                #     quantity=2,
                #     transaction_type=TransactionType.sell,
                #     date=datetime.datetime(2021, 9, 17),
                #     transaction_ex_rate=1.1416,
                #     tax=0,
                #     commission=12.95,
                # ),
                # Transaction(
                #     price=566.01,
                #     quantity=1,
                #     transaction_type=TransactionType.sell,
                #     date=datetime.datetime(2021, 9, 17),
                #     transaction_ex_rate=1.183396,
                #     tax=0,
                #     commission=12.95,
                # ),
                # Transaction(
                #     price=408,
                #     quantity=1,
                #     transaction_type=TransactionType.buy,
                #     date=datetime.datetime(2020, 10, 28),
                #     transaction_ex_rate=1.1338,
                #     tax=0,
                #     commission=3.95,
                # ),
                Transaction(
                    price=2.6,
                    quantity=2,  # field useless but required
                    transaction_type=TransactionType.dividend,
                    date=datetime.datetime(2021, 3, 29),
                    transaction_ex_rate=1.182248,
                    tax=1.93,
                ),
                # Transaction(
                #     price=0.16,
                #     quantity=50,  # field useless but required
                #     transaction_type=TransactionType.dividend,
                #     date=datetime.datetime(2022, 5, 25),
                #     transaction_ex_rate=1,
                #     tax=2.08,
                # ),
            ],
            Decimal("394.74"),
            Decimal("1.0219724"),
        )
    )
