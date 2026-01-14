import unittest
import pandas as pd
# 작성하신 함수들을 가져옵니다.
from ledger.services import calc_summary, calc_category_expense

class TestLedgerServices(unittest.TestCase):
    def setUp(self):
        """테스트용 가상 데이터 생성"""
        self.mock_data = pd.DataFrame([
            {"type": "수입", "category": "월급", "amount": 3000000},
            {"type": "수입", "category": "보너스", "amount": 500000},
            {"type": "지출", "category": "식비", "amount": 10000},
            {"type": "지출", "category": "식비", "amount": 15000},
            {"type": "지출", "category": "교통", "amount": 2000}
        ])

    def test_calc_summary_format_and_value(self):
        """1. 요약 통계가 int형으로, 정확한 값으로 반환되는지 확인"""
        income, expense, balance = calc_summary(self.mock_data)
        
        # 형식 확인: 반환된 값이 정수(int)인지 확인
        self.assertIsInstance(income, int)
        self.assertIsInstance(expense, int)
        self.assertIsInstance(balance, int)
        
        # 값 확인
        self.assertEqual(income, 3500000) # 300만 + 50만
        self.assertEqual(expense, 27000)  # 1만 + 1.5만 + 2천
        self.assertEqual(balance, 3473000) # 350만 - 2.7만

    def test_calc_category_expense_dict(self):
        """2. 카테고리별 합계가 딕셔너리 형태로 정확히 나오는지 확인"""
        result = calc_category_expense(self.mock_data)
        
        # 형식 확인: 반환값이 딕셔너리인지 확인
        self.assertIsInstance(result, dict)
        
        # 값 확인: 식비가 합쳐졌는지 확인
        self.assertEqual(result["식비"], 25000)
        self.assertEqual(result["교통"], 2000)
        # 수입 항목인 '월급'은 딕셔너리에 없어야 함
        self.assertNotIn("월급", result)

if __name__ == "__main__":
    unittest.main()