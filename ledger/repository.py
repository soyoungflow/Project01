import os
import pandas as pd


def load_transactions(path):
    # CSV 파일이 없으면 (앱 첫 실행) 빈 리스트 반환
    if not os.path.exists(path):
        return []

    # CSV 파일을 DataFrame(표 형태)으로 읽기
    df = pd.read_csv(path)

    # CSV가 비어 있으면 빈 리스트 반환
    if df.empty:
        return []

    # amount 컬럼을 숫자로 변환 (문자/빈값 → 0)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

    # DataFrame → list[dict] 변환 후 반환
    return df.to_dict(orient="records")


def save_transactions(path, transactions):
    # data 폴더가 없으면 생성 (저장 에러 방지)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 거래 리스트(list[dict])를 DataFrame으로 변환
    df = pd.DataFrame(transactions)

    # CSV 컬럼(헤더) 순서 고정
    columns = ["date", "type", "category", "description", "amount"]

    # 컬럼이 없을 경우 빈 값으로 생성
    for col in columns:
        if col not in df.columns:
            df[col] = ""

    # amount 컬럼을 정수형으로 정리
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

    # 컬럼 순서 적용
    df = df[columns]

    # CSV 파일로 저장 (index=False: 불필요한 인덱스 제거)
    df.to_csv(path, index=False, encoding="utf-8")