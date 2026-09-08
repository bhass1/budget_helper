import difflib
from enum import Enum, auto
from pathlib import Path
import pandas as pd
import logging
import re
import yaml

import util

TOOL_COLUMNS = ['Source', 'TransactionDate', 'Description', 'Amount', 'BH_Category']

class BankDb(Enum):
  CHASE_CREDIT_0 = ['Card', 'Transaction Date','Post Date','Description','Category','Type','Amount','Memo']
  CHASE_CREDIT_1 = ['Transaction Date','Post Date','Description','Category','Type','Amount','Memo']
  CHASE_SAVING_CHECKING = ['Details','Posting Date','Description','Amount','Type','Balance','Check or Slip #']
  AMEX_CREDIT = ['Date', 'Description', 'Card Member', 'Account #', 'Amount']
  UNKNOWN = []

  @staticmethod
  def detect_bank(columns):
    logging.debug(f'Using {columns} for bank detection')
    for bank in BankDb:
      try:
        if columns == bank.value:
          return bank
      except ValueError:
        pass
    return BankDb.UNKNOWN

class ExpenseCategorizer:

  _NORM_COLS = ['TransactionDate', 'Description', 'Amount']

  def __init__(self, category_map, source_map, bank_files, output, merge_file=None):
    self.cat_map_path = category_map
    self.source_map_path = source_map
    self.bank_files = bank_files
    self.output = output
    self.merge_file = merge_file
    self.prompt_fn = None

    with open(self.cat_map_path, 'r') as file:
      self.merchant_map = yaml.safe_load(file)
    self._load_source_map(self.source_map_path)
    logging.debug(self.merchant_map)

  def _load_source_map(self, source_map_path):
    with open(source_map_path, 'r') as file:
      self.source_map = yaml.safe_load(file)

    if not isinstance(self.source_map, dict) or not self.source_map:
      raise ValueError('Source map must contain at least one source mapping')

    for source, match_string in self.source_map.items():
      if not isinstance(source, str) or not isinstance(match_string, str):
        raise ValueError('Source map keys and values must be strings')

  def _source_for_file(self, in_file):
    filename = Path(in_file).name.lower()
    matches = [
      source for source, match_string in self.source_map.items()
      if match_string.lower() in filename
    ]

    if not matches:
      raise ValueError(f'No source matched input filename: {filename}')
    if len(matches) > 1:
      raise ValueError(
        f'Multiple sources matched input filename {filename}: {matches}'
      )

    return matches[0]

  @staticmethod
  def _detect_bank(columns):
      detected_bank = BankDb.detect_bank(columns)
      logging.info(f'Detected bank format {detected_bank.name}')
      return detected_bank

  def _normalize_database(self, df_bank_db):
    """ Given a DataFrame, normalize to three columns: TransactionDate, Description, and Amount """
    logging.debug(f'DataFrame columns {df_bank_db.columns}')
    logging.info('Detecting format of input file...')
    # Detect bank db type and extract 3 relevant columns
    detected_bank = ExpenseCategorizer._detect_bank(df_bank_db.columns.tolist())
    if (detected_bank == BankDb.CHASE_CREDIT_0 or 
        detected_bank == BankDb.CHASE_CREDIT_1):
      df_data = pd.DataFrame({
                ExpenseCategorizer._NORM_COLS[0]: df_bank_db['Transaction Date'], 
                ExpenseCategorizer._NORM_COLS[1]: df_bank_db['Description'], 
                ExpenseCategorizer._NORM_COLS[2]: df_bank_db['Amount']
                })
    elif detected_bank == BankDb.AMEX_CREDIT:
      df_data = pd.DataFrame({
                ExpenseCategorizer._NORM_COLS[0]: df_bank_db['Date'], 
                ExpenseCategorizer._NORM_COLS[1]: df_bank_db['Description'], 
                ExpenseCategorizer._NORM_COLS[2]: df_bank_db['Amount']
                })
      # Amex reports their data inverted from Chase, so we need to invert it here to normalize
      df_data[ExpenseCategorizer._NORM_COLS[2]] = df_data[ExpenseCategorizer._NORM_COLS[2]].apply(lambda x: -1*x)
    elif detected_bank == BankDb.CHASE_SAVING_CHECKING:
      df_data = pd.DataFrame({
                ExpenseCategorizer._NORM_COLS[0]: df_bank_db['Posting Date'],
                ExpenseCategorizer._NORM_COLS[1]: df_bank_db['Description'],
                ExpenseCategorizer._NORM_COLS[2]: df_bank_db['Amount']
                })
    else:
      raise NotImplementedError(f'Unknown input file format for {detected_bank=}')

    #Force datetime type on TransactionDate column
    df_data[ExpenseCategorizer._NORM_COLS[0]] = pd.to_datetime(df_data.TransactionDate)
    
    #Sanity check on return df_data
    for col in range(3):
      if ExpenseCategorizer._NORM_COLS[col] != df_data.columns[col]:
        raise KeyError(f'Column normalization failed - unexpected column {df_data.columns[col]}')
    
    return df_data

  def _find_best_match(in_word, word_dict):
      logging.debug(f'{word_dict=}')
      best_match={'category': "", 'match':"", 'size': 0}
      for category in word_dict:
        logging.debug(f'... against: {category}')
        for key in word_dict[category]:
          key = key.lower()
          key = re.sub(' +', ' ', key)
          logging.debug(f'... looking at: {key}')
          s = difflib.SequenceMatcher(None, key, in_word)
          matching_blocks = s.get_matching_blocks()
          logging.debug(f'... {matching_blocks=}')
          earliest_match = matching_blocks[0]
          match_size = earliest_match.size
          logging.debug(f'... earliest match length is: {match_size}')
          key_match_ratio = match_size / len(key)
          logging.debug(f'... {key_match_ratio=}')
          # First look at high quality matches, then take the biggest
          if key_match_ratio > 0.9:
            if match_size > best_match['size']:
              best_match['category'] = category
              best_match['match'] = key
              best_match['size'] = match_size
          # Always remove category when not accurate enough
          if best_match['size'] < 4:
            best_match['category'] = ''

      logging.debug(f'Found best match: {in_word} = {best_match}')
      return best_match


  def _categorize(self, df_data):
    bh_category = []
    for merch in df_data[ExpenseCategorizer._NORM_COLS[1]]:
      merch = merch.lower()
      merch = re.sub(' +', ' ', merch)
      logging.debug(f'Checking: {merch}')
      best_match = ExpenseCategorizer._find_best_match(merch, self.merchant_map)
      bh_category.append(best_match['category'])

    df_data = df_data.assign(BH_Category=bh_category)
    return df_data

  def _new_rows_for_sheet(self, existing_df, new_df):
    """Return the rows in new_df that are not already present in existing_df,
    deduplicated against existing rows by (Source, TransactionDate,
    Description, Amount). Duplicate new rows are retained so review mode can
    decide on each occurrence independently.

    Rows missing any key field raise a ValueError identifying the input and
    row number. Comparison is string-normalized (case-insensitive, whitespace
    collapsed) and amount-aware so equivalent rows match.
    """
    key_cols = ['Source', 'TransactionDate', 'Description', 'Amount']

    def _norm(value):
      if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
      if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
      if isinstance(value, (int, float)):
        return str(value)
      return re.sub(r'\s+', ' ', str(value).strip().lower())

    def _row_key(row, row_number, input_name):
      missing = [col for col in key_cols if _norm(row.get(col)) is None]
      if missing:
        raise ValueError(
            f'Input {input_name} row {row_number} is missing required '
            f'merge field(s): {", ".join(missing)}')
      return tuple(_norm(row.get(col)) for col in key_cols)

    existing_keys = set()
    for row_number, (_, row) in enumerate(existing_df.iterrows(), start=2):
      existing_keys.add(_row_key(row, row_number, 'merge workbook'))

    keep_idx = []
    for row_number, (idx, row) in enumerate(new_df.iterrows(), start=2):
      key = _row_key(row, row_number, 'new input')
      if key in existing_keys:
        continue
      keep_idx.append(idx)

    return new_df.loc[keep_idx].reset_index(drop=True)

  def _ask(self, message, default=True):
    if self.prompt_fn is not None:
      return self.prompt_fn(message, default)
    import click
    return click.confirm(message, default=default)

  def _sheet_action(self, sheet_name, row_count):
    message = f'Action for {sheet_name} ({row_count} new row(s))'
    if self.prompt_fn is not None:
      answer = self.prompt_fn(message, 'add')
      if answer is True:
        return 'add'
      if answer is False:
        return 'skip'
      return answer

    import click
    return click.prompt(message, type=click.Choice(
        ['add', 'review', 'skip'], case_sensitive=False), default='add')

  @staticmethod
  def _cell_value(value):
    if pd.isna(value):
      return None
    if isinstance(value, pd.Timestamp):
      return value.to_pydatetime()
    return value

  @staticmethod
  def _tool_column_positions(worksheet):
    positions = {}
    for cell in worksheet[1]:
      if cell.value in TOOL_COLUMNS:
        positions[cell.value] = cell.column
    next_column = worksheet.max_column + 1
    for column in TOOL_COLUMNS:
      if column not in positions:
        worksheet.cell(row=1, column=next_column, value=column)
        positions[column] = next_column
        next_column += 1
    return positions

  def _write_merged_workbook(self, path, sheet_data, sheet_order):
    from openpyxl import load_workbook

    workbook = load_workbook(path)
    for sheet_name in sheet_order:
      if sheet_name not in util.month_labels:
        continue
      worksheet = workbook[sheet_name]
      positions = self._tool_column_positions(worksheet)
      rows = sheet_data.get(sheet_name, pd.DataFrame(columns=TOOL_COLUMNS))
      start_row = worksheet.max_row + 1
      for offset, (_, row) in enumerate(rows.iterrows()):
        row_number = start_row + offset
        for column in TOOL_COLUMNS:
          worksheet.cell(
              row=row_number,
              column=positions[column],
              value=self._cell_value(row[column]))
    workbook.save(path)

  def _merge_into_workbook(self, df_month_data):
    """Merge per-month tool data into an existing workbook.

    Only month sheets (Jan..Dec) are considered. Non-month sheets are left
    untouched. Within a month sheet, only the tool columns (Source,
    TransactionDate, Description, Amount, BH_Category) are modified; other
    columns are preserved. New rows are appended after existing data.
    """
    merge_path = self.merge_file
    logging.info(f'Merging into {merge_path}')

    with pd.ExcelFile(merge_path) as xls:
      existing_sheets = xls.sheet_names
      existing_data = {s: pd.read_excel(xls, sheet_name=s) for s in existing_sheets}

    rows_to_write = {}
    month_labels = util.month_labels
    for mo in range(12):
      sheet_name = month_labels[mo]
      new_rows = df_month_data[mo]
      if new_rows.empty:
        continue
      if sheet_name not in existing_sheets:
        logging.info(f'Sheet {sheet_name} not in workbook; skipping')
        continue

      existing_df = existing_data[sheet_name]
      rows_to_add = self._new_rows_for_sheet(existing_df, new_rows)
      if rows_to_add.empty:
        logging.info(f'Sheet {sheet_name}: no new rows to add')
        continue

      logging.info(f'Sheet {sheet_name}: {len(rows_to_add)} new transaction(s)')
      for _, row in rows_to_add.iterrows():
        logging.info('  %s | %s | %s | %s',
                     row['Source'], row['TransactionDate'],
                     row['Description'], row['Amount'])

      decision = self._sheet_action(sheet_name, len(rows_to_add))
      if decision == 'skip':
        continue

      if decision == 'review':
        chosen = []
        for _, row in rows_to_add.iterrows():
          add = self._ask(
              f'  Add: {row["Source"]} | {row["TransactionDate"]} | '
              f'{row["Description"]} | {row["Amount"]}?', default=True)
          if add:
            chosen.append(row)
        rows_to_add = pd.DataFrame(chosen, columns=TOOL_COLUMNS)
        if rows_to_add.empty:
          continue

      rows_to_write[sheet_name] = rows_to_add

    self._write_merged_workbook(merge_path, rows_to_write, existing_sheets)

  def _append_rows(self, df, new_rows):
    """Append new_rows' tool columns into df at the first empty tool row,
    preserving any non-tool columns and their existing rows."""
    if df.empty:
      base = pd.DataFrame(columns=TOOL_COLUMNS)
      for col in new_rows.columns:
        if col not in base.columns:
          base[col] = pd.Series(dtype='object')
      df = base

    result = df.copy()
    for col in TOOL_COLUMNS:
      if col not in result.columns:
        result[col] = pd.Series(dtype='object')

    start = 0
    for i in range(len(result)):
      if all(pd.isna(result.loc[i, col]) for col in TOOL_COLUMNS):
        start = i
        break
    else:
      start = len(result)

    for offset, (_, row) in enumerate(new_rows.iterrows()):
      target = start + offset
      for col in TOOL_COLUMNS:
        result.loc[target, col] = row[col]
    return result

  def _write_workbook(self, path, sheet_data, sheet_order):
    with pd.ExcelWriter(path, engine='openpyxl', mode='a',
                        if_sheet_exists='overlay') as writer:
      for sheet_name in sheet_order:
        df = sheet_data[sheet_name]
        if not df.empty:
          df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
          pd.DataFrame(columns=TOOL_COLUMNS).to_excel(
              writer, sheet_name=sheet_name, index=False)

  def one_shot(self):
    """ Main function that does it all

        It reads bank files, detects bank type, normalizes the data, categorizes the data,
        splits the data by month, and writes the data to excel format.
    """
    df_all_data = pd.DataFrame()
  
    for in_file in self.bank_files:
      df_bank_db = pd.read_csv(in_file, index_col=False)
      source = self._source_for_file(in_file)
  
      logging.debug(df_bank_db)
  
      df_data = self._normalize_database(df_bank_db)

      logging.debug(df_data)
  
      df_data = self._categorize(df_data)
      df_data.insert(0, 'Source', source)

      if df_all_data.empty:
        df_all_data = df_data
      else:
        df_all_data = pd.concat([df_all_data, df_data], ignore_index=True)
      logging.debug(f'{df_data=}')
      logging.debug(f'{df_all_data=}')
  
    #Sort then split out the normalized and categorized data frame into different months
    df_all_data.sort_values(ExpenseCategorizer._NORM_COLS[0], inplace=True)
    df_month_data = []
    for mo in range(12):
      df_month_data.append(df_all_data[df_all_data[ExpenseCategorizer._NORM_COLS[0]].dt.month == mo+1])

    logging.debug(f'{df_month_data=}')

    if self.merge_file is not None:
      self._merge_into_workbook(df_month_data)
      return

    #Keep rows that are negative
    #df_data = df_data[df_data.Amount < 0] #FIXME: Do we really want to do this?
  
    #TODO FEAT: Read in existing month data and merge
    #df_existing = pd.read_excel("output/simple-out.xlsx")
  
  
    self.output.parent.mkdir(parents=True, exist_ok=True)
  
    logging.info(f'Writing output to {self.output}')
    with pd.ExcelWriter(self.output,
      mode="w",
      #mode="a",
      #if_sheet_exists="overlay",
    ) as writer:
      for mo in range(12):
        logging.debug(f'Month = {util.month_labels[mo]}')
        df_month_data[mo].to_excel(writer, sheet_name=util.month_labels[mo], index=False)

