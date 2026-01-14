import pandas as pd
# 레포지토리 함수들을 가져옵니다
from ledger.repository import load_transactions, COLUMNS

def get_transaction_df(path="data/ledger.csv"):
    """레포지토리 데이터를 읽어와서 서비스에서 쓸 수 있게 DF로 변환"""
    data = load_transactions(path)
    # 리스트 데이터를 다시 DF로 변환 (컬럼 순서 유지)
    return pd.DataFrame(data, columns=COLUMNS)

# 1. F3. 요약 통계 계산 함수
def calc_summary(df):
    """DataFrame을 받아 (총 수입, 총 지출, 잔액) 반환"""
    total_income = df[df['type'] == '수입']['amount'].sum()
    total_expense = df[df['type'] == '지출']['amount'].sum()
    balance = total_income - total_expense
    #int 값으로 변환하여 반환
    return int(total_income), int(total_expense), int(balance)

# 2. F5. 카테고리별 지출 통계 함수
def calc_category_expense(df):
    """카테고리별 지출 합계 계산"""
    expense_df = df[df['type'] == '지출']
    if expense_df.empty:
        return {}
        
    category_totals = expense_df.groupby('category')['amount'].sum()
    #딕셔너러리 값으로 변환하여 반환
    return category_totals.to_dict()