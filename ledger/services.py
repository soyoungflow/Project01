import pandas as pd

# 거래 내역 불러오기 함수 (이미 작성된 부분)
def load_transactions():
    return pd.read_csv("data/ledger.csv")

# 1. F3. 요약 통계 계산 함수
def calc_summary(transactions):
    """전체 거래 데이터프레임을 받아 (총 수입, 총 지출, 잔액) 반환"""
    # type이 '수입'인 행만 골라서 amount의 합계를 구함
    total_income = transactions[transactions['type'] == 'income']['amount'].sum()
    
    # type이 '지출'인 행만 골라서 amount의 합계를 구함
    total_expense = transactions[transactions['type'] == 'expense']['amount'].sum()

    balance = total_income - total_expense
    
    # 결과를 숫자로 반환 (판다스 sum의 결과는 숫자임)
    return int(total_income), int(total_expense), int(balance)

# 2. F5. 카테고리별 지출 통계 함수
def calc_category_expense(transactions):
    """지출 데이터프레임을 대상으로 카테고리별 합계 계산"""
    # 1. '지출' 데이터만 필터링
    expense_df = transactions[transactions['type'] == 'expense']
    
    # 2. 카테고리별로 그룹화하여 amount 합계 계산
    # .groupby('category')['amount'].sum()은 판다스의 핵심 기능입니다.
    category_totals = expense_df.groupby('category')['amount'].sum()

    # 3. 결과가 판다스 객체이므로, 쓰기 편하게 딕셔너리로 변환해서 반환
    return category_totals.to_dict()