import difflib
import pandas as pd
import logging
import yaml

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

  def _categorize(self, df_norm):
    bh_category = []
    for merch in df_norm[ExpenseCategorizer._NORM_COLS[1]]:
      merch = merch.lower()
      logging.debug(f'Checking: {merch}')
      best_match={'cat': "", 'match':"", 'size': 0}
      for cat in self.merchant_map:
        logging.debug(f'... against: {cat}')
        for key in self.merchant_map[cat]:
          key = key.lower()
          logging.debug(f'... looking at: {key}')
          s = difflib.SequenceMatcher(lambda x: x in ' ', merch, key)
          longest_match = s.find_longest_match()
          match_size = longest_match.size
          logging.debug(f'... longest match length is: {match_size}')
          if match_size > 1 and match_size > best_match['size']:
            best_match['cat'] = cat
            best_match['match'] = key
            best_match['size'] = match_size
          elif match_size > 1 and match_size == best_match['size']:
          # FIXME: Kroger shouldn't match kroger fuel; check against other keys in category_map
          # if match_size is equal, break tie by looking at other keys in category map for equal (?) match
          # kroger matches "kroger fuel" by 6 and "kroger' by 6. Keep "kroger" because it's more exact??
            if len(key) == match_size:
              logging.debug(f'... bugfix zone - match_size={match_size} best_match[size]={best_match["size"]}')
              best_match['cat'] = cat
              best_match['match'] = key
              best_match['size'] = match_size

      logging.debug(f'Found best match: {merch} = {best_match}')
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
  
  
    #Read in existing month data
    #df_existing = pd.read_excel("output/simple-out.xlsx")
  
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  
    self.output.parent.mkdir(parents=True, exist_ok=True)
  
    logging.info(f'Writing output to {self.output}')
    with pd.ExcelWriter(self.output,
      mode="w",
      #mode="a",
      #if_sheet_exists="overlay",
    ) as writer:
      for mo in range(12):
        logging.debug(f'Month = {month_labels[mo]}')
        df_norm_months[mo].to_excel(writer, sheet_name=month_labels[mo], index=False)


