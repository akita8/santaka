from pytest import mark, raises

# from santaka.models import NewStockTransaction
# from fastapi import HTTPException


class FakeRecord:
    def __init__(self, transaction_type, quantity):
        self.transaction_type = transaction_type
        self.quantity = quantity


@mark.parametrize(
    "records,transaction,expected_error",
    [
        # [[FakeRecord()], NewStockTransaction(), HTTPException]
    ],
)
def test_validate_stock_transaction(records, transaction, expected_error):
    with raises(expected_error):
        # this call checks that what is called inside
        # the with statement indeed raises the expected error
        pass  # TODO implement the test with correct parameters
