import logging
import os

month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def set_log_level():
  """ Set logging level from env var LOG_LEVEL """
  log_level = os.environ.get('LOG_LEVEL', 'INFO')
  if log_level == 'CRITICAL':
    logging.getLogger().setLevel(logging.CRITICAL)
  elif log_level == 'ERROR':
    logging.getLogger().setLevel(logging.ERROR)
  elif log_level == 'WARNING':
    logging.getLogger().setLevel(logging.WARNING)
  elif log_level == 'INFO':
    logging.getLogger().setLevel(logging.INFO)
  elif log_level == 'DEBUG':
    logging.getLogger().setLevel(logging.DEBUG)
  elif log_level == 'NOTSET':
    logging.getLogger().setLevel(logging.NOTSET)
  else:
    raise ValueError(f'Bad LOG_LEVEL given: {log_level=}')
