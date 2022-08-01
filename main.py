import pandas as pd


def main():
    df = pd.read_excel('test-01.xlsx', sheet_name="Sheet1")

    print(df)


    a = df["A"]
    b = df["B"] 

    print(f'len of a {len(a)}')

    for idx in range(len(a)):
       print(f'idx:{idx} {a[idx]}') 

if __name__=="__main__":
    main()

