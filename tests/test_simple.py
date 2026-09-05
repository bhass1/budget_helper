import os
import pandas as pd
import pandas.testing as pdt
import sys
import tempfile
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "budget_helper_bhass1"))
import expensecategorizer as ec

def test_simple_e2e(set_log, tmp_path):

  test_out = tmp_path / 'test-simple-out.xlsx'
  expenseCat = ec.ExpenseCategorizer(
      'tests/test-simple/categories.yml',
      'tests/test-simple/sources.yml',
      ['tests/test-simple/test-amex-credit-simple.csv', 'tests/test-simple/test-chase-credit-simple.csv'],
      test_out
  )

  expenseCat.one_shot()

  output_book = pd.ExcelFile(test_out)
  golden_book = pd.ExcelFile('tests/test-simple/golden.xlsx')
  assert output_book.sheet_names == golden_book.sheet_names

  for sheet_name in golden_book.sheet_names:
    df_test_out = pd.read_excel(output_book, sheet_name=sheet_name)
    df_test_golden = pd.read_excel(golden_book, sheet_name=sheet_name)
    df_test_out['TransactionDate'] = pd.to_datetime(df_test_out.TransactionDate)
    df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
    logging.info('%s output:\n%s', sheet_name, df_test_out)
    logging.info('%s golden:\n%s', sheet_name, df_test_golden)
    pdt.assert_frame_equal(df_test_out, df_test_golden, check_dtype=False)
