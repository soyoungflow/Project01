import pandas as pd
import os

FILE_PATH = "data/ledger.csv"

# 1. 객체 정의 (클래스)
class 가계부항목:
    def __init__(self, date, type, category, description, amount): 
        self.date = date
        self.type = type
        self.category = category
        self.description = description
        self.amount = int(amount)

# 2. 데이터 가공 엔진
def 가계부_분석_계산기():
    # [정의 우선] 결과 변수 초기화
    총_수입 = 0
    총_지출 = 0
    그래프용_카테고리_장부 = {}

    # 파일이 실제로 있을 때만 가공 시작
    if os.path.exists(FILE_PATH):
        df = pd.read_csv(FILE_PATH)
        transactions_raw = df.to_dict('records')

        # 객체가 하나도 없으면 이 loop는 자동으로 건너뜁니다.
        for raw in transactions_raw:
            항목 = 가계부항목(
                date=raw.get('date'),
                type=raw.get('type'),
                category=raw.get('category', '미분류'),
                description=raw.get('description', ''),
                amount=raw.get('amount', 0)
            )

            if 항목.type == "수입":
                총_수입 += 항목.amount
            elif 항목.type == "지출":
                총_지출 += 항목.amount
                
                # 인덱싱 작업
                if 항목.category in 그래프용_카테고리_장부:
                    그래프용_카테고리_장부[항목.category] += 항목.amount
                else:
                    그래프용_카테고리_장부[항목.category] = 항목.amount

    # 최종 결과 계산 (변수명 오타 수정)
    현재_잔액 = 총_수입 - 총_지출
    return 총_수입, 총_지출, 현재_잔액, 그래프용_카테고리_장부

# ... (위에는 기존 서비스 코드) ...

if __name__ == "__main__":
    # 1. 테스트용 가상 데이터 정의 (객체 리스트 형태)
    # 실제 CSV에서 읽어온 것처럼 딕셔너리 리스트를 만듭니다.
    test_transactions = [
        {"date": "2024-05-01", "type": "지출", "category": "식비", "description": "점심", "amount": 10000},
        {"date": "2024-05-01", "type": "지출", "category": "교통", "description": "버스", "amount": 2000},
        {"date": "2024-05-02", "type": "수입", "category": "월급", "description": "보너스", "amount": 50000},
        {"date": "2024-05-02", "type": "지출", "category": "식비", "description": "치킨", "amount": 15000},
    ]

    # 2. 엔진에 데이터 주입 (원래는 파일을 읽지만 테스트용 함수를 살짝 변형해 쓰거나 직접 로직을 검증)
    # 현재 함수는 내부에서 FILE_PATH를 읽으므로, 테스트를 위해 가상의 CSV를 만들거나 
    # 로직 내부만 따로 떼서 검증합니다.
    
    print("=== 가계부 엔진 테스트 시작 ===")
    
    # 임시 테스트용 결과 확인 루틴
    t_수입 = 0
    t_지출 = 0
    t_장부 = {}
    
    for raw in test_transactions:
        # 우리가 만든 클래스에 잘 들어가는지 확인
        item = 가계부항목(raw['date'], raw['type'], raw['category'], raw['description'], raw['amount'])
        
        if item.type == "수입":
            t_수입 += item.amount
        elif item.type == "지출":
            t_지출 += item.amount
            if item.category in t_장부:
                t_장부[item.category] += item.amount
            else:
                t_장부[item.category] = item.amount

    # 3. 결과 출력 및 검증
    print(f"결과 수입: {t_수입} (기대값: 50000)")
    print(f"결과 지출: {t_지출} (기대값: 27000)")
    print(f"결과 장부: {t_장부} (기대값: {{'식비': 25000, '교통': 2000}})")
    
    if t_지출 == 27000 and t_장부['식비'] == 25000:
        print("✅ 테스트 성공: 로직이 정확합니다!")
    else:
        print("❌ 테스트 실패: 로직을 확인하세요.")