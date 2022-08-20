import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "budget_helper_bhass1"))
import util

@pytest.fixture(scope='session')
def set_log():
  util.set_log_level()
