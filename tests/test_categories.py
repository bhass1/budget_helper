import os
import pandas as pd
import sys
import tempfile
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "budget_helper_bhass1"))
import expensecategorizer as ec

def test_categories_long_top_e2e(tmp_path):
  test_path = 'tests/test-categories/'
  test_out = tmp_path / 'test-categories-long-out.xlsx'
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'test-categories-long-top.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  df_test_long_out = pd.read_excel(test_out)
  df_test_long_out['TransactionDate'] = pd.to_datetime(df_test_long_out.TransactionDate)

  df_test_golden = pd.read_excel(test_path + 'golden.xlsx')
  df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
  assert df_test_long_out.equals(df_test_golden)

def test_categories_short_top_e2e(tmp_path):
  test_path = 'tests/test-categories/'

  test_out = tmp_path / 'test-categories-short-out.xlsx'
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'test-categories-short-top.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  df_test_short_out = pd.read_excel(test_out)
  df_test_short_out['TransactionDate'] = pd.to_datetime(df_test_short_out.TransactionDate)

  df_test_golden = pd.read_excel(test_path + 'golden.xlsx')
  df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
  assert df_test_short_out.equals(df_test_golden)
