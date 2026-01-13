import os
import pandas as pd
from pandas.errors import EmptyDataError

# 팀 규칙: 거래 데이터 컬럼(키) 고정
COLUMNS = ["date", "type", "category", "description", "amount"]


def load_transactions(path):
    """
    CSV 파일을 읽어서 거래 리스트(list[dict])로 반환
    - 파일이 없거나 비어 있으면 빈 리스트 반환
    """

    # CSV 파일이 아직 없으면 (앱 첫 실행) 빈 리스트
    if not os.path.exists(path):
        return []

    try:
        # CSV 파일을 DataFrame(표 형태)으로 읽기
        df = pd.read_csv(path)
    except EmptyDataError:
        # 파일은 있지만 내용이 완전히 비어 있는 경우
        return []

    # 행이 하나도 없으면 빈 리스트 반환
    if df.empty:
        return []

    # 컬럼이 누락된 경우 대비 (앱 전체 로직 보호)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # amount 컬럼을 숫자로 변환
    # 숫자로 변환 불가한 값은 NaN → 0 → int
    df["amount"] = (
        pd.to_numeric(df["amount"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    # 컬럼 순서를 팀 규칙대로 고정
    df = df[COLUMNS]

    # DataFrame → list[dict] 변환 후 반환
    return df.to_dict(orient="records")


def save_transactions(path, transactions):
    """
    거래 리스트(list[dict])를 CSV 파일로 저장
    - 항상 전체 데이터를 덮어쓰기 저장
    """

    # data 폴더가 없으면 생성 (저장 시 에러 방지)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 거래 리스트를 DataFrame으로 변환
    df = pd.DataFrame(transactions)

    # 컬럼 누락 대비 (저장 안정성 확보)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # amount 컬럼을 정수형으로 정리
    df["amount"] = (
        pd.to_numeric(df["amount"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    # 컬럼 순서 고정
    df = df[COLUMNS]

    # CSV 파일로 저장
    # index=False: 불필요한 인덱스 컬럼 저장 방지
    df.to_csv(path, index=False, encoding="utf-8")