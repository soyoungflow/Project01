# ledger/repository.py
# 역할: CSV 파일로 거래 목록을 저장/불러오기 하는 "저장소(Repository)" 계층
# UI(app.py)는 여기 함수를 호출만 하고, 파일 I/O 세부는 이 파일이 책임진다.

import os  # # 파일 존재 여부/경로 처리
import csv  # # CSV 읽기/쓰기

# # 거래 데이터의 "표준 컬럼" 약속(팀 공용 규격)
FIELDNAMES = ["date", "type", "category", "description", "amount"]  # # CSV 헤더 순서


def load_transactions(file_path: str) -> list[dict]:
    # # 의사코드:
    # # 1) file_path가 없으면 빈 리스트 반환
    # # 2) CSV를 열어서 DictReader로 한 줄씩 읽음
    # # 3) amount는 int로 변환 (CSV는 전부 문자열이기 때문)
    # # 4) 표준 dict 형태로 리스트 반환

    if not os.path.exists(file_path):  # # 파일 없으면(최초 실행)
        return []  # # 거래 없음

    transactions: list[dict] = []  # # 거래 목록 담을 리스트

    with open(file_path, "r", encoding="utf-8", newline="") as f:  # # CSV 열기
        reader = csv.DictReader(f)  # # {"date": "...", "type": "..."} 형태로 읽힘

        # # CSV 컬럼이 표준 규격과 다른 경우 최소 방어
        if reader.fieldnames is None:
            return []  # # 비정상 파일이면 빈 리스트
        missing = [c for c in FIELDNAMES if c not in reader.fieldnames]
        if missing:
            return []  # # 컬럼 누락이면 로드 실패(팀 규격 위반)

        for row in reader:  # # 각 거래(한 줄) 읽기
            try:
                amount = int(str(row["amount"]).strip())  # # 금액 문자열 -> int
            except Exception:
                # # 금액이 깨졌으면 그 줄은 스킵(앱이 죽지 않게)
                continue

            tx = {
                "date": str(row["date"]).strip(),  # # 날짜 문자열
                "type": str(row["type"]).strip(),  # # "지출"/"수입"
                "category": str(row["category"]).strip(),  # # 카테고리
                "description": str(row["description"]).strip(),  # # 메모
                "amount": amount,  # # 정수 금액
            }
            transactions.append(tx)  # # 리스트에 추가

    return transactions  # # 거래 목록 반환


def save_transactions(file_path: str, transactions: list[dict]) -> None:
    # # 의사코드:
    # # 1) data/ 폴더가 없으면 생성
    # # 2) CSV를 write 모드로 열어서(덮어쓰기)
    # # 3) header 작성 후, 모든 거래를 순서대로 저장

    # # 폴더 자동 생성 (ex: data/ledger.csv)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8", newline="") as f:  # # 덮어쓰기 저장
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)  # # 표준 헤더 고정
        writer.writeheader()  # # 첫 줄 헤더 쓰기

        for t in transactions:  # # 거래 하나씩 저장
            # # dict 키가 혹시 빠졌더라도 앱이 안 죽게 기본값 처리
            row = {
                "date": str(t.get("date", "")).strip(),
                "type": str(t.get("type", "")).strip(),
                "category": str(t.get("category", "")).strip(),
                "description": str(t.get("description", "")).strip(),
                "amount": int(t.get("amount", 0)),  # # int 보장
            }
            writer.writerow(row)  # # 한 줄 저장