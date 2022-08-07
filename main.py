import pandas as pd
import logging
import yaml
import difflib
import click

NORM_COLS = ['TransactionDate', 'Description', 'Amount']

def normalize_database(df_bank_db):
  """ Given a DataFrame, normalize to three columns: TransactionDate, Description, and Amount """
  logging.debug('DataFrame columns', df_bank_db.columns)
  logging.info('Detecting format of input file...')
  # Detect bank db type and extract 3 relevant columns
  if df_bank_db.columns[1] == 'Post Date':
    logging.info('Detected Chase Credit format')
    df_norm = pd.DataFrame({
              NORM_COLS[0]: df_bank_db['Transaction Date'], 
              NORM_COLS[1]: df_bank_db['Description'], 
              NORM_COLS[2]: df_bank_db['Amount']
              })
  elif df_bank_db.columns[2] == 'Card Member':
    logging.info('Detected American Express Credit format')
    df_norm = pd.DataFrame({
              NORM_COLS[0]: df_bank_db['Date'], 
              NORM_COLS[1]: df_bank_db['Description'], 
              NORM_COLS[2]: df_bank_db['Amount']
              })
    df_norm[NORM_COLS[2]] = df_norm[NORM_COLS[2]].apply(lambda x: -1*x)
  else:
    raise NotImplementedError('Unknown input file format')

  #Remove rows that are positive
  df_norm = df_norm[df_norm.Amount < 0]
  #Force datetime type on TransactionDate column
  df_norm[NORM_COLS[0]] = pd.to_datetime(df_norm.TransactionDate)

  for col in range(3):
    if NORM_COLS[col] != df_norm.columns[col]:
      raise KeyError(f'Column normalization failed - unexpected column {df_norm.columns[col]}')
  
  return df_norm

@click.command()
@click.argument('category_map', type=click.Path(exists=True), nargs=1)
@click.argument('bank_files', type=click.Path(exists=True), nargs=-1)
@click.argument('output', type=click.Path(), nargs=1)
def main(category_map, bank_files, output):
  """A CLI to help categorize exported expense databases from your bank"""

  logging.getLogger().setLevel(logging.DEBUG)

  with open(click.format_filename(category_map), 'r') as file:
    merchant_map = yaml.safe_load(file)

  logging.debug(merchant_map)

  df_norm_super = pd.DataFrame()

  for in_file in bank_files:
    df_bank_db = pd.read_csv(click.format_filename(in_file))

    logging.debug(df_bank_db)

    df_norm = normalize_database(df_bank_db)

    logging.debug(df_norm)

    bh_category = []
    for merch in df_norm[NORM_COLS[1]]:
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
    if df_norm_super.empty:
      df_norm_super = df_norm
    else:
      df_norm_super = pd.concat([df_norm_super, df_norm])
    logging.debug(f'DF_NORM: {df_norm}') 
    logging.debug(f'DF_NORM_SUPER: {df_norm_super}') 

  #Split out the normalized and categorized data frame into different months
  df_norm_months = []
  for mo in range(12):
    df_norm_months.append(df_norm[df_norm_super[NORM_COLS[0]].dt.month == mo+1])

  logging.debug(f'DF_NORM_MONTHS {df_norm_months}') 


  #Read in existing month data
  #df_existing = pd.read_excel("output/simple-out.xlsx")

  month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

  with pd.ExcelWriter(click.format_filename(output),
    mode="w",
    #mode="a",
    #if_sheet_exists="overlay",
  ) as writer:
    for mo in range(12):
      logging.debug(f'Month = {month_labels[mo]}')
      df_norm_months[mo].to_excel(writer, sheet_name=month_labels[mo], index=False)


if __name__=="__main__":
    main()

