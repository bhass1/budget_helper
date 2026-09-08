import pandas as pd
import pytest

import expensecategorizer as ec

TOOL_COLS = ['Source', 'TransactionDate', 'Description', 'Amount', 'BH_Category']

def _make_categorizer(tmp_path):
  cat_map = tmp_path / 'categories.yml'
  cat_map.write_text('Groceries:\n- kroger\n')
  source_map = tmp_path / 'sources.yml'
  source_map.write_text('source1: match1\n')
  return ec.ExpenseCategorizer.__new__(ec.ExpenseCategorizer)


def _tool_df(rows):
  return pd.DataFrame(rows, columns=TOOL_COLS)


def test_dedupe_new_rows_removes_duplicates(tmp_path):
  c = _make_categorizer(tmp_path)
  existing = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  new = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
      {'Source': 'source1', 'TransactionDate': '2022-01-02', 'Description': 'Kroger', 'Amount': -22.22, 'BH_Category': 'Groceries'},
  ])
  result = c._new_rows_for_sheet(existing, new)
  assert len(result) == 1
  assert result.iloc[0]['TransactionDate'] == '2022-01-02'


def test_dedupe_new_rows_keeps_first_duplicate(tmp_path):
  c = _make_categorizer(tmp_path)
  existing = _tool_df([])
  new = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  result = c._new_rows_for_sheet(existing, new)
  assert len(result) == 1
  assert result.iloc[0]['Description'] == 'Kroger'


def test_new_rows_ignores_rows_with_missing_key_fields(tmp_path):
  c = _make_categorizer(tmp_path)
  existing = _tool_df([])
  new = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
      {'Source': 'source1', 'TransactionDate': None, 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  result = c._new_rows_for_sheet(existing, new)
  assert len(result) == 1
  assert result.iloc[0]['Description'] == 'Kroger'


def _make_merge_categorizer(tmp_path, merge_file, bank_files):
  cat_map = tmp_path / 'categories.yml'
  cat_map.write_text('Groceries:\n- kroger\n')
  source_map = tmp_path / 'sources.yml'
  source_map.write_text('source1: match1\n')
  return ec.ExpenseCategorizer(
      str(cat_map), str(source_map), bank_files, None, merge_file=str(merge_file))


def _write_workbook(path, sheets):
  with pd.ExcelWriter(path, engine='openpyxl') as writer:
    for name, df in sheets.items():
      df.to_excel(writer, sheet_name=name, index=False)


def test_merge_adds_new_rows_to_existing_sheet(tmp_path):
  merge_file = tmp_path / 'budget.xlsx'
  existing = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  _write_workbook(merge_file, {'Jan': existing, 'Notes': pd.DataFrame({'Note': ['hello']})})

  bank = tmp_path / 'match1-bank.csv'
  bank.write_text('Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n'
                  '01/02/2022,01/03/2022,Kroger,Groceries,Sale,-22.22,\n'
                  '01/03/2022,01/04/2022,Kroger,Groceries,Sale,-33.33,\n')

  c = _make_merge_categorizer(tmp_path, merge_file, [str(bank)])
  c.prompt_fn = lambda msg, default=True: True  # add all
  c.one_shot()

  df = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(df) == 3
  assert df.iloc[1]['Amount'] == -22.22
  assert df.iloc[2]['Amount'] == -33.33
  # Non-month sheet preserved
  notes = pd.read_excel(merge_file, sheet_name='Notes')
  assert notes['Note'].tolist() == ['hello']


def test_merge_skips_sheet_when_prompt_no(tmp_path):
  merge_file = tmp_path / 'budget.xlsx'
  _write_workbook(merge_file, {'Jan': _tool_df([])})

  bank = tmp_path / 'match1-bank.csv'
  bank.write_text('Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n'
                  '01/02/2022,01/03/2022,Kroger,Groceries,Sale,-22.22,\n')

  c = _make_merge_categorizer(tmp_path, merge_file, [str(bank)])
  c.prompt_fn = lambda msg, default=True: False  # skip
  c.one_shot()

  df = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(df) == 0


def test_merge_review_each_row(tmp_path):
  merge_file = tmp_path / 'budget.xlsx'
  _write_workbook(merge_file, {'Jan': _tool_df([])})

  bank = tmp_path / 'match1-bank.csv'
  bank.write_text('Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n'
                  '01/02/2022,01/03/2022,Kroger,Groceries,Sale,-22.22,\n'
                  '01/03/2022,01/04/2022,Kroger,Groceries,Sale,-33.33,\n')

  c = _make_merge_categorizer(tmp_path, merge_file, [str(bank)])
  answers = iter(['review', True, False])
  c.prompt_fn = lambda msg, default=True: next(answers)
  c.one_shot()

  df = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(df) == 1
  assert df.iloc[0]['Amount'] == -22.22


def test_merge_does_not_duplicate_existing_rows(tmp_path):
  merge_file = tmp_path / 'budget.xlsx'
  existing = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  _write_workbook(merge_file, {'Jan': existing})

  bank = tmp_path / 'match1-bank.csv'
  bank.write_text('Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n'
                  '01/01/2022,01/03/2022,Kroger,Groceries,Sale,-11.11,\n'
                  '01/02/2022,01/03/2022,Kroger,Groceries,Sale,-22.22,\n')

  c = _make_merge_categorizer(tmp_path, merge_file, [str(bank)])
  c.prompt_fn = lambda msg, default=True: True
  c.one_shot()

  df = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(df) == 2
  assert df.iloc[1]['Amount'] == -22.22