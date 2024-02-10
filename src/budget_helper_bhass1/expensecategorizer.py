import difflib
from enum import Enum, auto
import pandas as pd
import logging
import re
import yaml

import util

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

  def __init__(self, category_map, bank_files, output):
    self.cat_map_path = category_map
    self.bank_files = bank_files
    self.output = output

    with open(self.cat_map_path, 'r') as file:
      self.merchant_map = yaml.safe_load(file)
    logging.debug(self.merchant_map)

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

  def one_shot(self):
    """ Main function that does it all

        It reads bank files, detects bank type, normalizes the data, categorizes the data,
        splits the data by month, and writes the data to excel format.
    """
    df_all_data = pd.DataFrame()
  
    for in_file in self.bank_files:
      df_bank_db = pd.read_csv(in_file, index_col=False)
  
      logging.debug(df_bank_db)
  
      df_data = self._normalize_database(df_bank_db)

      logging.debug(df_data)
  
      df_data = self._categorize(df_data)

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

