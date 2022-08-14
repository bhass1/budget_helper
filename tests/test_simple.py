import os
import pandas as pd
import sys
import tempfile
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "budget_helper_bhass1"))
import expensecategorizer as ec

def test_simple(tmp_path):

  test_out = tmp_path / 'test-simple-out.xlsx'
  expenseCat = ec.ExpenseCategorizer(
      'tests/test-simple/test-categories.yml',
      ['tests/test-simple/test-amex-credit-simple.csv', 'tests/test-simple/test-chase-credit-simple.csv'],
      test_out
  )

  expenseCat.one_shot()

  logging.getLogger().setLevel(logging.INFO)
  df_test_out = pd.read_excel(test_out)
  df_test_out['TransactionDate'] = pd.to_datetime(df_test_out.TransactionDate)
  logging.info(df_test_out)
  df_test_golden = pd.read_excel('tests/test-simple/test-out-simple.xlsx')
  df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
  logging.info(df_test_golden)
  assert df_test_out.equals(df_test_golden)
