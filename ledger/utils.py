# ledger/utils.py
# 역할: 공용 유틸리티 함수 (형식 변환, 검증 등)

from datetime import date, datetime
from typing import Optional, Union


def format_currency(amount: Union[int, float]) -> str:
    """
    금액을 보기 좋은 원화 형식으로 변환
    
    Args:
        amount: 금액 (정수 또는 실수)
    
    Returns:
        "1,000원" 형식의 문자열
    
    Examples:
        >>> format_currency(1000)
        '1,000원'
        >>> format_currency(1500000)
        '1,500,000원'
    """
    try:
        return f"{int(amount):,}원"
    except (ValueError, TypeError):
        return "0원"


def parse_date(date_input: Union[str, date, datetime]) -> Optional[date]:
    """
    다양한 형식의 날짜 입력을 date 객체로 변환
    
    Args:
        date_input: 날짜 문자열, date 객체, 또는 datetime 객체
    
    Returns:
        date 객체 또는 변환 실패시 None
    
    Examples:
        >>> parse_date("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> parse_date(datetime(2024, 1, 15))
        datetime.date(2024, 1, 15)
    """
    # 이미 date 객체인 경우
    if isinstance(date_input, date):
        return date_input

    # datetime 객체인 경우
    if isinstance(date_input, datetime):
        return date_input.date()

    # 문자열인 경우 파싱 시도
    if isinstance(date_input, str):
        formats = [
            "%Y-%m-%d",  # 2024-01-15
            "%Y/%m/%d",  # 2024/01/15
            "%Y.%m.%d",  # 2024.01.15
            "%Y%m%d",    # 20240115
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_input.strip(), fmt).date()
            except ValueError:
                continue

    return None


def validate_amount(amount: any) -> bool:
    """
    금액 값이 유효한지 검증
    
    Args:
        amount: 검증할 금액 값
    
    Returns:
        유효하면 True, 아니면 False
    
    Examples:
        >>> validate_amount(1000)
        True
        >>> validate_amount(-100)
        False
        >>> validate_amount("abc")
        False
    """
    try:
        amt = int(amount)
        return amt >= 0
    except (ValueError, TypeError):
        return False


def get_month_range(year: int, month: int) -> tuple[date, date]:
    """
    특정 연월의 시작일과 마지막일을 반환
    
    Args:
        year: 연도
        month: 월 (1-12)
    
    Returns:
        (시작일, 마지막일) 튜플
    
    Examples:
        >>> get_month_range(2024, 1)
        (datetime.date(2024, 1, 1), datetime.date(2024, 1, 31))
    """
    start = date(year, month, 1)

    # 마지막 날 계산
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    # 하루 빼서 해당 월의 마지막 날로
    from datetime import timedelta
    end = end - timedelta(days=1)

    return start, end


def safe_str(value: any, default: str = "") -> str:
    """
    값을 안전하게 문자열로 변환
    
    Args:
        value: 변환할 값
        default: 변환 실패시 반환할 기본값
    
    Returns:
        문자열
    """
    if value is None:
        return default
    try:
        return str(value).strip()
    except Exception:
        return default


def safe_int(value: any, default: int = 0) -> int:
    """
    값을 안전하게 정수로 변환
    
    Args:
        value: 변환할 값
        default: 변환 실패시 반환할 기본값
    
    Returns:
        정수
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default