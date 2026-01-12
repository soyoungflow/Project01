# 1. F3. 요약 통계 계산 함수
def calc_summary(transactions):
    """전체 거래 리스트를 받아 (총 수입, 총 지출, 잔액) 반환"""
    total_income = 0
    total_expense = 0

    for item in transactions:
        if item.type == "수입":
            total_income += item.amount
        elif item.type == "지출":
            total_expense += item.amount

    balance = total_income - total_expense
    return total_income, total_expense, balance

# 2. F5. 카테고리별 지출 통계 함수
def get_category_stats(transactions):
    """지출 데이터만 대상으로 카테고리별 합계 계산"""
    category_totals = {}

    for item in transactions:
        if item.type == "지출":
            if item.category in category_totals:
                category_totals[item.category] += item.amount
            else:
                category_totals[item.category] = item.amount

    return category_totals