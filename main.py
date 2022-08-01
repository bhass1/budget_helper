import pandas as pd
import logging
import yaml
import difflib


def normalize_database(df_bank_db):
  logging.debug('Our columns', df_bank_db.columns)
  # Detect bank db type and extract 3 relevant columns
  if df_bank_db.columns[1] == 'Post Date':
    logging.info('Detected Chase Credit format')
    df_norm = pd.DataFrame({
              'TransactionDate': df_bank_db['Transaction Date'], 
              'Description': df_bank_db['Description'], 
              'Amount': df_bank_db['Amount']
              })
  elif df_bank_db.columns[2] == 'Card Member':
    logging.info('Detected American Express Credit format')
    df_norm = pd.DataFrame({
              'TransactionDate': df_bank_db['Date'], 
              'Description': df_bank_db['Description'], 
              'Amount': df_bank_db['Amount']
              })
    df_norm['Amount'] = df_norm['Amount'].apply(lambda x: -1*x)

  #Remove rows that are positive
  df_norm = df_norm[df_norm.Amount < 0]
  #Force datetime type on TransactionDate column
  df_norm['TransactionDate'] = pd.to_datetime(df_norm.TransactionDate)
  
  return df_norm

def main():

  logging.getLogger().setLevel(logging.DEBUG)

  df_bank_db = pd.read_csv('test/test-simple/test-amex-credit-simple.csv')

  logging.debug(df_bank_db)

  df_norm = normalize_database(df_bank_db)

  logging.debug(df_norm)

  with open('test/test-simple/test-categories.yml', 'r') as file:
    merchant_map = yaml.safe_load(file)

  logging.debug(merchant_map)

  bh_category = []
  for merch in df_norm['Description']:
    merch = merch.lower()
    logging.debug(f'Checking: {merch}')
    best_match={'cat': "", 'match':"", 'size': 0}
    for cat in merchant_map:
      logging.debug(f'... against: {cat}')
      for key in merchant_map[cat]:
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
  
    logging.debug(f'Found best match: {merch} = {best_match}')    
    bh_category.append(best_match['cat'])

  df_norm = df_norm.assign(BH_Category=bh_category)
  logging.debug(df_norm) 

  #Split out the normalized and categorized data frame into different months
  df_norm_months = []
  for mo in range(12):
    df_norm_months.append(df_norm[df_norm['TransactionDate'].dt.month == mo+1])

  logging.debug(df_norm_months) 


  #Read in existing month data
  #df_existing = pd.read_excel("output/simple-out.xlsx")

  month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

  with pd.ExcelWriter("output/out-simple.xlsx",
    mode="w",
    #mode="a",
    #if_sheet_exists="overlay",
  ) as writer:
    for mo in range(12):
      df_norm_months[mo].to_excel(writer, sheet_name=month_labels[mo], index=False)


if __name__=="__main__":
    main()

