import pandas as pd
import tempfile
import logging

import expensecategorizer as ec

def test_categories_long_top_e2e(set_log, tmp_path):
  test_path = 'tests/test-categories/'
  test_out = tmp_path / ('test_out.xlsx')
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'categories-long-top.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  df_test_long_out = pd.read_excel(test_out)
  df_test_long_out['TransactionDate'] = pd.to_datetime(df_test_long_out.TransactionDate)

  df_test_golden = pd.read_excel(test_path + 'golden.xlsx')
  df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
  logging.debug(f'{df_test_long_out=}')
  logging.debug(f'{df_test_golden=}')
  assert df_test_long_out.equals(df_test_golden)

def test_categories_short_top_e2e(set_log, tmp_path):
  test_path = 'tests/test-categories/'
  test_out = tmp_path / ('test_out.xlsx')
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'categories-short-top.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  df_test_short_out = pd.read_excel(test_out)
  df_test_short_out['TransactionDate'] = pd.to_datetime(df_test_short_out.TransactionDate)

  df_test_golden = pd.read_excel(test_path + 'golden.xlsx')
  df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
  logging.debug(f'{df_test_short_out=}')
  logging.debug(f'{df_test_golden=}')
  assert df_test_short_out.equals(df_test_golden)
