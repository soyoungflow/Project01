# ledger.py
from datetime import datetime
from typing import List, Dict, Optional

# 거래 목록
transactions: List[Dict] = []

def create_transaction(
    date: str,
    trade_type: str,
    category: str,
    amount: int,
    description: Optional[str] = None
) -> Dict:
    """
    거래 1건을 딕셔너리로 생성 + 거래 목록에 추가
    순서:
        1. 날짜
        2. 거래종류 (수입/지출)
        3. 분류 (카테고리)
        4. 설명
        5. 금액
        6. 기록시각 (자동)
    """
    transaction = {
        "date": date,
        "type": trade_type,
        "category": category,
        "description": description,
        "amount": amount,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    transactions.append(transaction)
    return transaction


# categories.py

# 수입 카테고리
INCOME_CATEGORIES = [
    {"name": "급여", "type": "수입", "is_fixed": False},
    {"name": "이자", "type": "수입", "is_fixed": False},
    {"name": "할인적립", "type": "수입", "is_fixed": False},
    {"name": "투자수익", "type": "수입", "is_fixed": False},
    {"name": "기타", "type": "수입", "is_fixed": False},
]

# 고정 지출 카테고리
FIXED_EXPENSE_CATEGORIES = [
    {"name": "주거", "type": "지출", "is_fixed": True},
    {"name": "통신", "type": "지출", "is_fixed": True},
    {"name": "보험", "type": "지출", "is_fixed": True},
    {"name": "상환", "type": "지출", "is_fixed": True},
    {"name": "교육", "type": "지출", "is_fixed": True},
]

# 변동 지출 카테고리
VARIABLE_EXPENSE_CATEGORIES = [
    {"name": "식비", "type": "지출", "is_fixed": False},
    {"name": "교통비", "type": "지출", "is_fixed": False},
    {"name": "생활용품", "type": "지출", "is_fixed": False},
    {"name": "의류", "type": "지출", "is_fixed": False},
    {"name": "미용", "type": "지출", "is_fixed": False},
    {"name": "건강", "type": "지출", "is_fixed": False},
    {"name": "여행", "type": "지출", "is_fixed": False},
    {"name": "경조사", "type": "지출", "is_fixed": False},
    {"name": "기타", "type": "지출", "is_fixed": False},
]


# ledger.py
from datetime import datetime
from typing import List, Dict, Optional

# 거래 목록
transactions: List[Dict] = []

def create_transaction(
    date: str,
    trade_type: str,
    category: str,
    amount: int,
    description: Optional[str] = None
) -> Dict:
    """
    거래 1건을 딕셔너리로 생성 + 거래 목록에 추가
    포함항목:
       날짜, 거래종류, 분류, 설명, 금액, 기록시각
    """
    transaction = {
        "date": date,                              # 날짜
        "type": trade_type,                        # 수입/지출
        "category": category,                      # 분류
        "description": description,                # 설명
        "amount": amount,                          # 금액
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 기록시각 자동
    }
    transactions.append(transaction)
    return transaction


# budget.py   ## 초과예산 부분 아까 성중님이 다 작업하신거 같긴한데...
from typing import List, Dict

# 예산 목록 리스트
budgets: List[Dict] = []

def add_budget(category: str, limit: int):
    """
    카테고리별 예산을 추가
    """
    budgets.append({"category": category, "limit": limit})

def is_over_budget(category: str, spent: int) -> bool:
    """
    카테고리별 지출이 예산을 초과했는지 판단
    """
    for b in budgets:
        if b["category"] == category:
            return spent > b["limit"]
    return False
