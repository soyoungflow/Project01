# ledger/models.py
# 역할: 거래(Transaction) 데이터 구조 정의 (도메인 모델)

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Transaction:
    """거래 한 건의 데이터 구조"""

    date: date  # 날짜
    type: str  # "지출" 또는 "수입"
    category: str  # 카테고리 (식비, 교통, 통신, 생활, 기타 등)
    description: str  # 내용/메모
    amount: int  # 금액(원 단위, 정수)

    def __post_init__(self):
        """데이터 유효성 검증"""
        # type은 "지출" 또는 "수입"만 허용
        if self.type not in ["지출", "수입"]:
            raise ValueError(f"잘못된 구분: {self.type}. '지출' 또는 '수입'만 가능합니다.")

        # 금액은 0 이상이어야 함
        if self.amount < 0:
            raise ValueError(f"금액은 0 이상이어야 합니다: {self.amount}")

        # 카테고리가 비어있으면 "기타"로 설정
        if not self.category or self.category.strip() == "":
            self.category = "기타"

    def to_dict(self) -> dict:
        """Transaction을 dict로 변환 (CSV 저장용)"""
        return {
            "date": self.date,
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "amount": self.amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """dict에서 Transaction 생성 (CSV 로드용)"""
        return cls(
            date=data["date"],
            type=data["type"],
            category=data["category"],
            description=data["description"],
            amount=data["amount"],
        )


def validate_transaction_dict(data: dict) -> bool:
    """거래 데이터(dict)의 유효성 검증"""
    required_keys = ["date", "type", "category", "description", "amount"]

    # 필수 키 확인
    for key in required_keys:
        if key not in data:
            return False

    # type 값 검증
    if data["type"] not in ["지출", "수입"]:
        return False

    # amount 값 검증
    try:
        amount = int(data["amount"])
        if amount < 0:
            return False
    except (ValueError, TypeError):
        return False

    return True