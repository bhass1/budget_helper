import tempfile
import pandas as pd
from .context import budget_helper_bhass1 as bhb

def test_simple(tmp_path):

    test_out = tmp_path / 'test-simple-out.xlsx'
    expenseCat = bhb.ExpenseCategorizer(
        'test-simple/test-categories.yml',

        ['test-simple/test-amex-credit-simple.csv', 'test-simple/test-chase-credit-simple.csv'],
        test_out
    )

    expenseCat.one_shot()

    df_test_out = pd.read_excel(test_out)
    df_test_golden = pd.read_excel('test-simple/test-out-simple.xlsx')
    assert df_test_out.equals(df_test_golden)
