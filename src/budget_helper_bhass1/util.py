import logging
import os

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
