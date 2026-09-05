import pandas as pd
import pandas.testing as pdt
import pytest
import tempfile
import logging

import expensecategorizer as ec

def test_source_is_selected_from_filename(tmp_path):
    source_map = tmp_path / 'sources.yml'
    source_map.write_text('source1: match1\nsource2: match2\n')

    categorizer = ec.ExpenseCategorizer.__new__(ec.ExpenseCategorizer)
    categorizer._load_source_map(source_map)

    assert categorizer._source_for_file('/imports/2024-match1-export.csv') == 'source1'
    assert categorizer._source_for_file('/imports/match2-export.csv') == 'source2'


def test_source_filename_must_match_a_source(tmp_path):
    source_map = tmp_path / 'sources.yml'
    source_map.write_text('source1: match1\nsource2: match2\n')

    categorizer = ec.ExpenseCategorizer.__new__(ec.ExpenseCategorizer)
    categorizer._load_source_map(source_map)

    with pytest.raises(ValueError, match='No source matched'):
        categorizer._source_for_file('/imports/unknown.csv')


def test_source_filename_cannot_match_multiple_sources(tmp_path):
    source_map = tmp_path / 'sources.yml'
    source_map.write_text('source1: export\nsource2: match2-export\n')

    categorizer = ec.ExpenseCategorizer.__new__(ec.ExpenseCategorizer)
    categorizer._load_source_map(source_map)

    with pytest.raises(ValueError, match='Multiple sources matched'):
        categorizer._source_for_file('/imports/match2-export.csv')

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


def _assert_output_matches_golden(test_out, golden_path):
  output_book = pd.ExcelFile(test_out)
  golden_book = pd.ExcelFile(golden_path)
  assert output_book.sheet_names == golden_book.sheet_names

  for sheet_name in golden_book.sheet_names:
    df_test_out = pd.read_excel(output_book, sheet_name=sheet_name)
    df_test_golden = pd.read_excel(golden_book, sheet_name=sheet_name)
    df_test_out['TransactionDate'] = pd.to_datetime(df_test_out.TransactionDate)
    df_test_golden['TransactionDate'] = pd.to_datetime(df_test_golden.TransactionDate)
    logging.debug('%s output:\n%s', sheet_name, df_test_out)
    logging.debug('%s golden:\n%s', sheet_name, df_test_golden)
    pdt.assert_frame_equal(df_test_out, df_test_golden, check_dtype=False)

def test_categories_long_top_e2e(set_log, tmp_path):
  test_path = 'tests/test-categories/'
  test_out = tmp_path / ('test_out.xlsx')
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'categories-long-top.yml',
      test_path + 'sources.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  _assert_output_matches_golden(test_out, test_path + 'golden.xlsx')

def test_categories_short_top_e2e(set_log, tmp_path):
  test_path = 'tests/test-categories/'
  test_out = tmp_path / ('test_out.xlsx')
  expenseCat = ec.ExpenseCategorizer(
      test_path + 'categories-short-top.yml',
      test_path + 'sources.yml',
      [test_path + 'test-chase-credit-short-top.csv', test_path + 'test-chase-credit-long-top.csv'],
      test_out
  )

  expenseCat.one_shot()

  _assert_output_matches_golden(test_out, test_path + 'golden.xlsx')
