import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as app_module


def test_normalize_txn_type_supports_debit_and_credit():
    assert app_module.normalize_txn_type('Debit') == 'Expense'
    assert app_module.normalize_txn_type('Credit') == 'Income'
    assert app_module.normalize_txn_type('Expense') == 'Expense'
    assert app_module.normalize_txn_type('Income') == 'Income'
    assert app_module.normalize_txn_type('Not Reported') == 'Not Reported'
