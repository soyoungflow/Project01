# ledger/services.py
# 역할: "계산/통계"만 담당하는 비즈니스 로직 계층
# UI(app.py)는 여기 함수들을 호출만 한다.

from collections import defaultdict  # 카테고리 합계 만들 때 편함


def calc_summary(transactions: list[dict]) -> tuple[int, int, int]:
    # 의사코드:
    # 1) income=0, expense=0
    # 2) 거래를 돌면서 type이 "수입"이면 income에 더함
    # 3) type이 "지출"이면 expense에 더함
    # 4) balance = income - expense
    # 5) (income, expense, balance) 반환

    income = 0  # 총 수입
    expense = 0  # 총 지출

    for t in transactions:  # 거래 하나씩 확인
        t_type = str(t.get("type", "")).strip()  # "지출"/"수입"
        amount = int(t.get("amount", 0))  # 금액(정수)

        if t_type == "수입":  # 수입이면
            income += amount
        elif t_type == "지출":  # 지출이면
            expense += amount

    balance = income - expense  # 잔액
    return income, expense, balance


def calc_category_expense(transactions: list[dict]) -> dict[str, int]:
    # 의사코드:
    # 1) 지출(type=="지출")만 대상으로 한다
    # 2) category별로 amount를 누적한다
    # 3) {"식비": 22000, "교통": 4500, ...} 형태로 반환

    totals = defaultdict(int)  # 없는 키는 0부터 시작

    for t in transactions:
        if str(t.get("type", "")).strip() != "지출":  # 지출만
            continue

        category = str(t.get("category", "기타")).strip() or "기타"  # 비면 기타
        amount = int(t.get("amount", 0))  # 금액
        totals[category] += amount  # 카테고리별 누적

    return dict(totals)

