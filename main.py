import pandas as pd


def main():
    df_excel = pd.read_excel('test/test-01.xlsx', sheet_name="Sheet1")

    print(df_excel)
    a = df_excel["A"]
    b = df_excel["B"] 

    print(f'len of a {len(a)}')

    for idx in range(len(a)):
       print(f'idx:{idx} {a[idx]}') 

    df_csv = pd.read_csv('test/test-chase-credit-01.csv')

    print(df_csv)


if __name__=="__main__":
    main()

