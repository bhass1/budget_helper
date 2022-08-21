import difflib
import pandas as pd
import logging
import re
import yaml

import util

class ExpenseCategorizer:

  _NORM_COLS = ['TransactionDate', 'Description', 'Amount']

  def __init__(self, category_map, bank_files, output):
    self.cat_map_path = category_map
    self.bank_files = bank_files
    self.output = output

    with open(self.cat_map_path, 'r') as file:
      self.merchant_map = yaml.safe_load(file)
    logging.debug(self.merchant_map)

  def _normalize_database(self, df_bank_db):
    """ Given a DataFrame, normalize to three columns: TransactionDate, Description, and Amount """
    logging.debug(f'DataFrame columns {df_bank_db.columns}')
    logging.info('Detecting format of input file...')
    # Detect bank db type and extract 3 relevant columns
    if df_bank_db.columns[1] == 'Post Date':
      logging.info('Detected Chase Credit format')
      df_norm = pd.DataFrame({
                ExpenseCategorizer._NORM_COLS[0]: df_bank_db['Transaction Date'], 
                ExpenseCategorizer._NORM_COLS[1]: df_bank_db['Description'], 
                ExpenseCategorizer._NORM_COLS[2]: df_bank_db['Amount']
                })
    elif df_bank_db.columns[2] == 'Card Member':
      logging.info('Detected American Express Credit format')
      df_norm = pd.DataFrame({
                ExpenseCategorizer._NORM_COLS[0]: df_bank_db['Date'], 
                ExpenseCategorizer._NORM_COLS[1]: df_bank_db['Description'], 
                ExpenseCategorizer._NORM_COLS[2]: df_bank_db['Amount']
                })
      df_norm[ExpenseCategorizer._NORM_COLS[2]] = df_norm[ExpenseCategorizer._NORM_COLS[2]].apply(lambda x: -1*x)
    else:
      raise NotImplementedError('Unknown input file format')
    
    #Remove rows that are positive
    df_norm = df_norm[df_norm.Amount < 0]
    #Force datetime type on TransactionDate column
    df_norm[ExpenseCategorizer._NORM_COLS[0]] = pd.to_datetime(df_norm.TransactionDate)
    
    for col in range(3):
      if ExpenseCategorizer._NORM_COLS[col] != df_norm.columns[col]:
        raise KeyError(f'Column normalization failed - unexpected column {df_norm.columns[col]}')
    
    return df_norm

  def _find_best_match(in_word, word_dict):
      logging.debug(f'{word_dict=}')
      best_match={'cat': "", 'match':"", 'size': 0}
      for cat in word_dict:
        logging.debug(f'... against: {cat}')
        for key in word_dict[cat]:
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
              best_match['cat'] = cat
              best_match['match'] = key
              best_match['size'] = match_size
          # Always remove category when not accurate enough
          if best_match['size'] < 4:
            best_match['cat'] = ''

      logging.debug(f'Found best match: {in_word} = {best_match}')
      return best_match


  def _categorize(self, df_norm):
    bh_category = []
    for merch in df_norm[ExpenseCategorizer._NORM_COLS[1]]:
      merch = merch.lower()
      merch = re.sub(' +', ' ', merch)
      logging.debug(f'Checking: {merch}')
      best_match = ExpenseCategorizer._find_best_match(merch, self.merchant_map)
      bh_category.append(best_match['cat'])

    df_norm = df_norm.assign(BH_Category=bh_category)
    return df_norm

  def one_shot(self):
  
    df_norm_super = pd.DataFrame()
  
    for in_file in self.bank_files:
      df_bank_db = pd.read_csv(in_file)
  
      logging.debug(df_bank_db)
  
      df_norm = self._normalize_database(df_bank_db)
  
      logging.debug(df_norm)
  
      df_norm = self._categorize(df_norm)

      if df_norm_super.empty:
        df_norm_super = df_norm
      else:
        df_norm_super = pd.concat([df_norm_super, df_norm], ignore_index=True)
      logging.debug(f'{df_norm=}')
      logging.debug(f'{df_norm_super=}')
  
    #Sort then split out the normalized and categorized data frame into different months
    df_norm_super.sort_values(ExpenseCategorizer._NORM_COLS[0], inplace=True)
    df_norm_months = []
    for mo in range(12):
      df_norm_months.append(df_norm_super[df_norm_super[ExpenseCategorizer._NORM_COLS[0]].dt.month == mo+1])
  
    logging.debug(f'{df_norm_months=}')
  
  
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
        df_norm_months[mo].to_excel(writer, sheet_name=util.month_labels[mo], index=False)


