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


def test_new_duplicates_are_kept_for_individual_review(tmp_path):
  c = _make_categorizer(tmp_path)
  existing = _tool_df([])
  new = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])
  result = c._new_rows_for_sheet(existing, new)
  assert len(result) == 2
  assert result.iloc[0]['Description'] == 'Kroger'
  assert result.iloc[1]['Description'] == 'Kroger'


def test_new_rows_reports_missing_key_fields(tmp_path):
  c = _make_categorizer(tmp_path)
  existing = _tool_df([])
  new = _tool_df([
      {'Source': 'source1', 'TransactionDate': '2022-01-01', 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
      {'Source': 'source1', 'TransactionDate': None, 'Description': 'Kroger', 'Amount': -11.11, 'BH_Category': 'Groceries'},
  ])

  with pytest.raises(ValueError, match='row 3.*TransactionDate'):
    c._new_rows_for_sheet(existing, new)


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
  c.prompt_fn = lambda msg, default=True: 'add'
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
  c.prompt_fn = lambda msg, default=True: 'skip'
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
  c.prompt_fn = lambda msg, default=True: 'add'
  c.one_shot()

  df = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(df) == 2
  assert df.iloc[1]['Amount'] == -22.22


def test_merge_fixture_covers_overlap_duplicates_empty_and_preservation(tmp_path):
  merge_file = tmp_path / 'existing_budget.xlsx'
  jan = pd.DataFrame({
      'Source': ['source1'], 'TransactionDate': ['2022-01-05'],
      'Description': ['KROGER #100'], 'Amount': [-45.10],
      'BH_Category': ['Groceries'], 'Budget': ['monthly groceries']})
  feb = pd.DataFrame({
      'Source': ['source1'], 'TransactionDate': ['2022-02-02'],
      'Description': ['CITY ELECTRIC'], 'Amount': [-120.00],
      'BH_Category': ['Utilities'], 'Budget': ['already paid']})
  notes = pd.DataFrame({'Note': ['preserve this sheet'], 'Value': [123]})
  _write_workbook(merge_file, {'Jan': jan, 'Feb': feb, 'Mar': _tool_df([]), 'Notes': notes})

  fixture_dir = 'tests/test-merge/'
  bank_files = [
      fixture_dir + 'source1_jan_feb.csv',
      fixture_dir + 'source2_feb_mar.csv',
      fixture_dir + 'empty_source1.csv',
  ]
  c = ec.ExpenseCategorizer(
      fixture_dir + 'categories.yml', fixture_dir + 'sources.yml',
      bank_files, None, merge_file=str(merge_file))
  c.prompt_fn = lambda message, default='add': 'add'
  c.one_shot()

  jan_out = pd.read_excel(merge_file, sheet_name='Jan')
  feb_out = pd.read_excel(merge_file, sheet_name='Feb')
  mar_out = pd.read_excel(merge_file, sheet_name='Mar')
  notes_out = pd.read_excel(merge_file, sheet_name='Notes')

  assert jan_out['Description'].tolist() == ['KROGER #100', 'CAFE LUNA']
  assert feb_out['Description'].tolist() == [
      'CITY ELECTRIC', 'CITY ELECTRIC', 'CITY ELECTRIC',
      'MYSTERY MERCHANT', 'KROGER FUEL #22']
  assert mar_out['Description'].tolist() == ['NO THAI', 'NO THAI', 'ALDI']
  assert jan_out['Budget'].iloc[0] == 'monthly groceries'
  assert pd.isna(jan_out['Budget'].iloc[1])
  assert feb_out['Budget'].iloc[0] == 'already paid'
  assert feb_out['Budget'].iloc[1:].isna().all()
  assert list(jan_out.columns) == ['Source', 'TransactionDate', 'Description', 'Amount', 'BH_Category', 'Budget']
  assert list(feb_out.columns) == ['Source', 'TransactionDate', 'Description', 'Amount', 'BH_Category', 'Budget']
  assert list(mar_out.columns) == ['Source', 'TransactionDate', 'Description', 'Amount', 'BH_Category']
  assert notes_out.to_dict('records') == [
      {'Note': 'preserve this sheet', 'Value': 123}]
  assert set(jan_out['Source']) == {'source1'}
  assert set(feb_out['Source']) == {'source1', 'source2'}
  assert set(mar_out['Source']) == {'source2'}


def test_merge_fixture_review_can_skip_one_duplicate(tmp_path):
  merge_file = tmp_path / 'existing_budget.xlsx'
  _write_workbook(merge_file, {'Mar': pd.DataFrame()})
  fixture_dir = 'tests/test-merge/'
  c = ec.ExpenseCategorizer(
      fixture_dir + 'categories.yml', fixture_dir + 'sources.yml',
      [fixture_dir + 'source2_feb_mar.csv'], None,
      merge_file=str(merge_file))
  answers = iter(['review', True, False, True])
  c.prompt_fn = lambda message, default='add': next(answers)
  c.one_shot()

  mar_out = pd.read_excel(merge_file, sheet_name='Mar')
  assert mar_out['Description'].tolist() == ['NO THAI', 'ALDI']
  assert mar_out['Amount'].tolist() == [-42.00, -61.20]


def test_merge_covers_every_month_sheet(tmp_path):
  merge_file = tmp_path / 'all_months.xlsx'
  month_sheets = {
      month: _tool_df([]) for month in [
          'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
          'Aug', 'Sep', 'Oct', 'Nov', 'Dec']}
  _write_workbook(merge_file, month_sheets)

  fixture_dir = 'tests/test-merge/'
  c = ec.ExpenseCategorizer(
      fixture_dir + 'categories.yml', fixture_dir + 'sources.yml',
      [fixture_dir + 'source1_apr_dec.csv'], None,
      merge_file=str(merge_file))
  c.prompt_fn = lambda message, default='add': 'add'
  c.one_shot()

  expected = {
      'Apr': ('KROGER #APR', 'source1'),
      'May': ('CAFE LUNA #MAY', 'source1'),
      'Jun': ('CITY ELECTRIC #JUN', 'source1'),
      'Jul': ('KROGER FUEL #JUL', 'source1'),
      'Aug': ('ALDI #AUG', 'source1'),
      'Sep': ('MYSTERY MERCHANT #SEP', 'source1'),
      'Oct': ('KROGER #OCT', 'source1'),
      'Nov': ('CAFE LUNA #NOV', 'source1'),
      'Dec': ('CITY ELECTRIC #DEC', 'source1'),
  }
  for month in month_sheets:
    output = pd.read_excel(merge_file, sheet_name=month)
    if month in expected:
      description, source = expected[month]
      assert output['Description'].tolist() == [description]
      assert output['Source'].tolist() == [source]
    else:
      assert output.empty
      assert list(output.columns) == TOOL_COLS

  assert pd.ExcelFile(merge_file).sheet_names == list(month_sheets)


def test_merging_same_input_twice_does_not_add_duplicate_rows(tmp_path):
  merge_file = tmp_path / 'already_merged.xlsx'
  _write_workbook(merge_file, {'Jan': _tool_df([]), 'Feb': _tool_df([])})

  fixture_dir = 'tests/test-merge/'
  input_file = fixture_dir + 'source1_jan_feb.csv'
  first_merge = ec.ExpenseCategorizer(
      fixture_dir + 'categories.yml', fixture_dir + 'sources.yml',
      [input_file], None, merge_file=str(merge_file))
  first_merge.prompt_fn = lambda message, default='add': 'add'
  first_merge.one_shot()

  first_output = pd.read_excel(merge_file, sheet_name='Jan')
  first_feb_output = pd.read_excel(merge_file, sheet_name='Feb')
  assert len(first_output) == 2
  assert len(first_feb_output) == 2

  prompt_calls = []
  second_merge = ec.ExpenseCategorizer(
      fixture_dir + 'categories.yml', fixture_dir + 'sources.yml',
      [input_file], None, merge_file=str(merge_file))
  second_merge.prompt_fn = lambda message, default='add': prompt_calls.append(message)
  second_merge.one_shot()

  second_output = pd.read_excel(merge_file, sheet_name='Jan')
  assert len(second_output) == 2
  assert second_output[['Source', 'TransactionDate', 'Description', 'Amount']].equals(
      first_output[['Source', 'TransactionDate', 'Description', 'Amount']])
  assert prompt_calls == []

  feb_output = pd.read_excel(merge_file, sheet_name='Feb')
  assert len(feb_output) == 2
  assert feb_output[['Source', 'TransactionDate', 'Description', 'Amount']].equals(
      first_feb_output[['Source', 'TransactionDate', 'Description', 'Amount']])
  assert pd.ExcelFile(merge_file).sheet_names == ['Jan', 'Feb']
