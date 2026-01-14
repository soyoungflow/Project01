# ledger/services.py
# 역할: 비즈니스 로직 (계산/통계) 담당
# UI(app.py)는 여기 함수들을 호출만 한다.

from collections import defaultdict
from typing import Optional


def calc_summary(transactions: list[dict]) -> tuple[int, int, int]:
    """
    거래 목록에서 총 수입, 총 지출, 잔액을 계산
    
    Args:
        transactions: 거래 목록 (dict 리스트)
    
    Returns:
        (총수입, 총지출, 잔액) 튜플
    
    Examples:
        >>> calc_summary([
        ...     {"type": "수입", "amount": 3000000},
        ...     {"type": "지출", "amount": 500000}
        ... ])
        (3000000, 500000, 2500000)
    """
    income = 0  # 총 수입
    expense = 0  # 총 지출

    for t in transactions:
        t_type = str(t.get("type", "")).strip()
        amount = int(t.get("amount", 0))

        if t_type == "수입":
            income += amount
        elif t_type == "지출":
            expense += amount

    balance = income - expense
    return income, expense, balance


def calc_detailed_summary(transactions: list[dict]) -> dict:
    """
    거래 목록의 상세 통계를 계산
    
    Args:
        transactions: 거래 목록 (dict 리스트)
    
    Returns:
        상세 통계 dict
        {
            "total_income": 총수입,
            "total_expense": 총지출,
            "balance": 잔액,
            "income_count": 수입 거래 수,
            "expense_count": 지출 거래 수,
            "avg_income": 평균 수입,
            "avg_expense": 평균 지출
        }
    """
    income_total = 0
    expense_total = 0
    income_count = 0
    expense_count = 0

    for t in transactions:
        t_type = str(t.get("type", "")).strip()
        amount = int(t.get("amount", 0))

        if t_type == "수입":
            income_total += amount
            income_count += 1
        elif t_type == "지출":
            expense_total += amount
            expense_count += 1

    return {
        "total_income": income_total,
        "total_expense": expense_total,
        "balance": income_total - expense_total,
        "income_count": income_count,
        "expense_count": expense_count,
        "avg_income": income_total // income_count if income_count > 0 else 0,
        "avg_expense": expense_total // expense_count if expense_count > 0 else 0,
    }


def calc_category_expense(transactions: list[dict]) -> dict[str, int]:
    """
    카테고리별 지출 합계를 계산 (지출만 대상)
    
    Args:
        transactions: 거래 목록 (dict 리스트)
    
    Returns:
        {"식비": 25000, "교통": 5000, ...} 형태의 dict
    
    Examples:
        >>> calc_category_expense([
        ...     {"type": "지출", "category": "식비", "amount": 10000},
        ...     {"type": "지출", "category": "식비", "amount": 15000},
        ...     {"type": "지출", "category": "교통", "amount": 5000}
        ... ])
        {'식비': 25000, '교통': 5000}
    """
    totals = defaultdict(int)

    for t in transactions:
        if str(t.get("type", "")).strip() != "지출":
            continue

        category = str(t.get("category", "기타")).strip() or "기타"
        amount = int(t.get("amount", 0))
        totals[category] += amount

    return dict(totals)


def calc_budget_status(
    spent: int, budget: int
) -> tuple[float, str, str]:
    """
    예산 대비 지출 상태를 계산
    
    Args:
        spent: 실제 지출액
        budget: 예산액
    
    Returns:
        (진행률, 상태, 메시지) 튜플
        - 진행률: 0.0 ~ 1.0 (또는 초과시 1.0 이상)
        - 상태: "정상" | "경고" | "초과"
        - 메시지: 사용자에게 보여줄 메시지
    
    Examples:
        >>> calc_budget_status(500000, 1000000)
        (0.5, '정상', '예산 범위 내에서 관리 중입니다.')
        
        >>> calc_budget_status(850000, 1000000)
        (0.85, '경고', '예산의 80%를 사용했습니다!')
        
        >>> calc_budget_status(1100000, 1000000)
        (1.1, '초과', '예산을 초과했습니다! 지금부터는 지출을 강하게 줄여야 합니다.')
    """
    if budget == 0:
        return 0.0, "미설정", "예산을 설정하면 관제 경고가 정확해집니다."

    ratio = spent / budget

    if ratio >= 1.0:
        status = "초과"
        message = "🚨 예산을 초과했습니다! 지금부터는 지출을 강하게 줄여야 합니다."
    elif ratio >= 0.8:
        status = "경고"
        message = "⚠️ 예산의 80%를 사용했습니다!"
    else:
        status = "정상"
        message = "👍 예산 범위 내에서 관리 중입니다."

    return ratio, status, message


def filter_transactions_by_period(
    transactions: list[dict],
    start_date,
    end_date
) -> list[dict]:
    """
    기간으로 거래 필터링
    
    Args:
        transactions: 거래 목록
        start_date: 시작일
        end_date: 종료일
    
    Returns:
        필터링된 거래 목록
    """
    return [
        t for t in transactions
        if start_date <= t.get("date") <= end_date
    ]


def filter_transactions_by_type(
    transactions: list[dict],
    transaction_type: str
) -> list[dict]:
    """
    구분(지출/수입)으로 거래 필터링
    
    Args:
        transactions: 거래 목록
        transaction_type: "지출" 또는 "수입"
    
    Returns:
        필터링된 거래 목록
    """
    return [
        t for t in transactions
        if str(t.get("type", "")).strip() == transaction_type
    ]


def filter_transactions_by_category(
    transactions: list[dict],
    category: str
) -> list[dict]:
    """
    카테고리로 거래 필터링
    
    Args:
        transactions: 거래 목록
        category: 카테고리명
    
    Returns:
        필터링된 거래 목록
    """
    return [
        t for t in transactions
        if str(t.get("category", "")).strip() == category
    ]


def search_transactions(
    transactions: list[dict],
    keyword: str
) -> list[dict]:
    """
    내용(description)으로 거래 검색
    
    Args:
        transactions: 거래 목록
        keyword: 검색 키워드
    
    Returns:
        검색 결과 거래 목록
    """
    if not keyword.strip():
        return transactions

    keyword_lower = keyword.strip().lower()
    return [
        t for t in transactions
        if keyword_lower in str(t.get("description", "")).lower()
    ]


def get_top_expense_categories(
    transactions: list[dict],
    limit: int = 5
) -> list[tuple[str, int]]:
    """
    지출이 많은 카테고리 TOP N 반환
    
    Args:
        transactions: 거래 목록
        limit: 반환할 개수
    
    Returns:
        [(카테고리명, 지출액), ...] 리스트 (내림차순)
    
    Examples:
        >>> get_top_expense_categories([...], limit=3)
        [('식비', 250000), ('교통', 50000), ('통신', 30000)]
    """
    category_totals = calc_category_expense(transactions)
    sorted_items = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return sorted_items[:limit]