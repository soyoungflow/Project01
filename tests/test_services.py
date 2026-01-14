# tests/test_services.py
# 역할: 서비스(비즈니스 로직) 계층 테스트

import unittest
from ledger.services import (
    calc_summary,
    calc_category_expense,
    calc_budget_status,
    filter_transactions_by_type,
    get_top_expense_categories,
)


class TestCalcSummary(unittest.TestCase):
    """calc_summary 함수 테스트"""

    def test_basic_calculation(self):
        """기본 수입/지출 계산"""
        transactions = [
            {"type": "수입", "category": "월급", "amount": 3000000},
            {"type": "수입", "category": "보너스", "amount": 500000},
            {"type": "지출", "category": "식비", "amount": 10000},
            {"type": "지출", "category": "식비", "amount": 15000},
            {"type": "지출", "category": "교통", "amount": 2000},
        ]

        income, expense, balance = calc_summary(transactions)

        # 형식 확인
        self.assertIsInstance(income, int)
        self.assertIsInstance(expense, int)
        self.assertIsInstance(balance, int)

        # 값 확인
        self.assertEqual(income, 3500000)  # 300만 + 50만
        self.assertEqual(expense, 27000)  # 1만 + 1.5만 + 2천
        self.assertEqual(balance, 3473000)  # 350만 - 2.7만

    def test_empty_list(self):
        """빈 리스트 처리"""
        income, expense, balance = calc_summary([])
        self.assertEqual(income, 0)
        self.assertEqual(expense, 0)
        self.assertEqual(balance, 0)

    def test_only_income(self):
        """수입만 있는 경우"""
        transactions = [
            {"type": "수입", "amount": 1000000},
            {"type": "수입", "amount": 500000},
        ]
        income, expense, balance = calc_summary(transactions)
        self.assertEqual(income, 1500000)
        self.assertEqual(expense, 0)
        self.assertEqual(balance, 1500000)

    def test_only_expense(self):
        """지출만 있는 경우"""
        transactions = [
            {"type": "지출", "amount": 10000},
            {"type": "지출", "amount": 5000},
        ]
        income, expense, balance = calc_summary(transactions)
        self.assertEqual(income, 0)
        self.assertEqual(expense, 15000)
        self.assertEqual(balance, -15000)


class TestCalcCategoryExpense(unittest.TestCase):
    """calc_category_expense 함수 테스트"""

    def test_category_grouping(self):
        """카테고리별 그룹핑"""
        transactions = [
            {"type": "수입", "category": "월급", "amount": 3000000},
            {"type": "지출", "category": "식비", "amount": 10000},
            {"type": "지출", "category": "식비", "amount": 15000},
            {"type": "지출", "category": "교통", "amount": 2000},
        ]

        result = calc_category_expense(transactions)

        # 형식 확인
        self.assertIsInstance(result, dict)

        # 값 확인
        self.assertEqual(result["식비"], 25000)
        self.assertEqual(result["교통"], 2000)

        # 수입 항목은 포함되지 않음
        self.assertNotIn("월급", result)

    def test_empty_list(self):
        """빈 리스트 처리"""
        result = calc_category_expense([])
        self.assertEqual(result, {})

    def test_default_category(self):
        """카테고리가 없을 때 '기타'로 처리"""
        transactions = [
            {"type": "지출", "category": "", "amount": 5000},
            {"type": "지출", "category": "기타", "amount": 3000},
        ]
        result = calc_category_expense(transactions)
        self.assertEqual(result["기타"], 8000)


class TestCalcBudgetStatus(unittest.TestCase):
    """calc_budget_status 함수 테스트"""

    def test_normal_status(self):
        """정상 상태 (50% 사용)"""
        ratio, status, message = calc_budget_status(500000, 1000000)
        self.assertEqual(ratio, 0.5)
        self.assertEqual(status, "정상")
        self.assertIn("범위", message)

    def test_warning_status(self):
        """경고 상태 (85% 사용)"""
        ratio, status, message = calc_budget_status(850000, 1000000)
        self.assertEqual(ratio, 0.85)
        self.assertEqual(status, "경고")
        self.assertIn("80%", message)

    def test_exceeded_status(self):
        """초과 상태 (110% 사용)"""
        ratio, status, message = calc_budget_status(1100000, 1000000)
        self.assertGreater(ratio, 1.0)
        self.assertEqual(status, "초과")
        self.assertIn("초과", message)

    def test_zero_budget(self):
        """예산이 0인 경우"""
        ratio, status, message = calc_budget_status(100000, 0)
        self.assertEqual(ratio, 0.0)
        self.assertEqual(status, "미설정")


class TestFilterTransactions(unittest.TestCase):
    """거래 필터링 함수 테스트"""

    def setUp(self):
        """테스트용 데이터"""
        self.transactions = [
            {"type": "수입", "category": "월급", "amount": 3000000},
            {"type": "지출", "category": "식비", "amount": 10000},
            {"type": "지출", "category": "교통", "amount": 5000},
        ]

    def test_filter_by_type(self):
        """구분으로 필터링"""
        expenses = filter_transactions_by_type(self.transactions, "지출")
        self.assertEqual(len(expenses), 2)

        incomes = filter_transactions_by_type(self.transactions, "수입")
        self.assertEqual(len(incomes), 1)


class TestTopExpenseCategories(unittest.TestCase):
    """지출 TOP 카테고리 테스트"""

    def test_top_categories(self):
        """TOP N 카테고리 반환"""
        transactions = [
            {"type": "지출", "category": "식비", "amount": 100000},
            {"type": "지출", "category": "교통", "amount": 50000},
            {"type": "지출", "category": "통신", "amount": 30000},
            {"type": "지출", "category": "생활", "amount": 20000},
        ]

        top3 = get_top_expense_categories(transactions, limit=3)

        self.assertEqual(len(top3), 3)
        self.assertEqual(top3[0], ("식비", 100000))
        self.assertEqual(top3[1], ("교통", 50000))
        self.assertEqual(top3[2], ("통신", 30000))


if __name__ == "__main__":
    unittest.main()