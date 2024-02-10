import pandas as pd
import tempfile
import logging

import expensecategorizer as ec

def test_categories_mid_partial(set_log):
    merch = "black bandit"
    key1 = "abc ack banda ccccc"
    key2 = "xyz aaa aaaaa"
    test_dict = {
      'key1': [ key1 ],
      'key2': [ key2 ]
    }
    expected = ''
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

    test_dict['key2'] = [ "black bandit" ]
    expected = 'key2'
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

def test_categories_end_partial(set_log):
    merch = "kega 6aaaaaaaa"
    key1 = "abc ack 6aaaaaaaa"
    key2 = "xyz aaa"
    test_dict = {
      'key1': [ key1 ],
      'key2': [ key2 ]
    }
    expected = ''
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

    test_dict['key2'] = [ "kega 6" ]
    expected = 'key2'
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

def test_categories_substring(set_log):
    merch = "chicken 999"
    key1 = "chicken fuel"
    key2 = "chicken"
    expected = 'key2'
    test_dict = {
      'key1': [ key1 ],
      'key2': [ key2 ]
    }
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

    test_dict['key1'] = [ key2 ]
    test_dict['key2'] = [ key1 ]
    expected = 'key1'
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

def test_categories_superstring(set_log):
    merch = "chicken fuel #1337"
    key1 = "chicken fuel"
    key2 = "chicken"
    expected = 'key1'
    test_dict = {
      'key1': [ key1 ],
      'key2': [ key2 ]
    }
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

    test_dict['key1'] = [ key2 ]
    test_dict['key2'] = [ key1 ]
    expected = 'key2'
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

def test_categories_ignoreprefix(set_log):
    merch = "tst* lobster - drift city"
    key1 = "chicken fuel drift city"
    key2 = "chicken"
    expected = ''
    test_dict = {
      'key1': [ key1 ],
      'key2': [ key2 ]
    }
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']

    test_dict['key2'] = [ 'lobster' ]
    expected = 'key2'
    best_match = ec.ExpenseCategorizer._find_best_match(merch, test_dict)
    assert expected == best_match['category']


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
