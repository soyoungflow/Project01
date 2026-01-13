import unittest
import pandas as pd
# 파일 구조에 따라 import 경로는 유지합니다.
from ledger.services import calc_summary, calc_category_expense  

class TestServices(unittest.TestCase):
    def setUp(self):
        """테스트 데이터 준비"""
        data_list = [
            {"type": "수입", "category": "급여", "amount": 3000000},
            {"type": "수입", "category": "부수입", "amount": 100000},
            {"type": "지출", "category": "식비", "amount": 10000},
            {"type": "지출", "category": "식비", "amount": 20000},
            {"type": "지출", "category": "교통", "amount": 1500},
            {"type": "지출", "category": "교통", "amount": 1500},
            {"type": "지출", "category": "쇼핑", "amount": 50000},
            {"type": "지출", "category": "쇼핑", "amount": 30000},
            {"type": "지출", "category": "의료", "amount": 15000},
            {"type": "지출", "category": "기타", "amount": 2000}
        ]
        self.transactions = pd.DataFrame(data_list)

    def test_calc_summary(self):
        """요약 통계 계산 검증"""
        total_income, total_expense, balance = calc_summary(self.transactions)
        
        # 기대값: 수입(310만), 지출(13만), 잔액(297만)
        self.assertEqual(total_income, 3100000)
        self.assertEqual(total_expense, 130000)
        self.assertEqual(balance, 2970000)

    def test_calc_category_expense(self):
        """카테고리별 지출 합계 딕셔너리 검증"""
        category_stats_dict = calc_category_expense(self.transactions)
        
        expected_data = {
            "식비": 30000,
            "교통": 3000,
            "쇼핑": 80000,
            "의료": 15000,
            "기타": 2000
        }
        
        self.assertDictEqual(category_stats_dict, expected_data)
        self.assertEqual(len(category_stats_dict), 5)

if __name__ == "__main__":
    unittest.main()