import unittest
import sys
import os
from types import SimpleNamespace

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledger.services import calc_summary, get_category_stats

class TestServices(unittest.TestCase):
    def test_logic(self):
        # 1. 테스트 데이터 10개 준비 (수입 2개, 지출 8개)
        data = [
            SimpleNamespace(type="수입", category="급여", amount=3000000),
            SimpleNamespace(type="수입", category="부수입", amount=100000),
            SimpleNamespace(type="지출", category="식비", amount=10000),
            SimpleNamespace(type="지출", category="식비", amount=20000),
            SimpleNamespace(type="지출", category="교통", amount=1500),
            SimpleNamespace(type="지출", category="교통", amount=1500),
            SimpleNamespace(type="지출", category="쇼핑", amount=50000),
            SimpleNamespace(type="지출", category="쇼핑", amount=30000),
            SimpleNamespace(type="지출", category="의료", amount=15000),
            SimpleNamespace(type="지출", category="기타", amount=2000)
        ]

        # 2. 요약 통계 검증 (F3)
        # 총 수입: 3,100,000 / 총 지출: 130,000 / 잔액: 2,970,000
        income, expense, balance = calc_summary(data)
        self.assertEqual(income, 3100000)
        self.assertEqual(expense, 130000)
        self.assertEqual(balance, 2970000)

        # 3. 카테고리별 지출 통계 검증 (F5)
        stats = get_category_stats(data)
        self.assertEqual(stats["식비"], 30000)    # 10,000 + 20,000
        self.assertEqual(stats["교통"], 3000)     # 1,500 + 1,500
        self.assertEqual(stats["쇼핑"], 80000)    # 50,000 + 30,000
        self.assertEqual(stats["의료"], 15000)
        self.assertEqual(stats["기타"], 2000)
        self.assertEqual(len(stats), 5)           # 지출 카테고리 총 5개

if __name__ == "__main__":
    unittest.main()