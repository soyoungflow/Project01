import unittest
import pandas as pd
from ledger.services import calc_summary, get_category_stats

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
        """본 파일의 변수명 total_income, total_expense, balance와 맞춰서 검증"""
        # 서비스 파일의 리턴 순서와 이름을 맞춥니다.
        total_income, total_expense, balance = calc_summary(self.transactions)
        
        self.assertEqual(total_income, 3100000)
        self.assertEqual(total_expense, 130000)
        self.assertEqual(balance, 2970000)

    def test_get_category_stats(self):
        """본 파일의 변수명 category_totals가 딕셔너리로 변환된 결과를 검증"""
        # 결과값 변수명도 직관적으로 구성
        category_stats_dict = get_category_stats(self.transactions)
        
        expected_data = {
            "식비": 30000,
            "교통": 3000,
            "쇼핑": 80000,
            "의료": 15000,
            "기타": 2000
        }
        
        # 딕셔너리 비교
        self.assertDictEqual(category_stats_dict, expected_data)
        self.assertEqual(len(category_stats_dict), 5)

if __name__ == "__main__":
    unittest.main()