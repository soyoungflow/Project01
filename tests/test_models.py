# tests/test_models.py
# 역할: Transaction 모델 테스트

import unittest
from datetime import date
from ledger.models import Transaction, validate_transaction_dict


class TestTransaction(unittest.TestCase):
    """Transaction 클래스 테스트"""

    def test_valid_transaction_creation(self):
        """정상적인 거래 생성"""
        tx = Transaction(
            date=date(2024, 1, 15),
            type="지출",
            category="식비",
            description="점심",
            amount=10000,
        )

        self.assertEqual(tx.date, date(2024, 1, 15))
        self.assertEqual(tx.type, "지출")
        self.assertEqual(tx.category, "식비")
        self.assertEqual(tx.description, "점심")
        self.assertEqual(tx.amount, 10000)

    def test_invalid_type(self):
        """잘못된 구분(type) 거부"""
        with self.assertRaises(ValueError):
            Transaction(
                date=date(2024, 1, 15),
                type="잘못된타입",
                category="식비",
                description="점심",
                amount=10000,
            )

    def test_negative_amount(self):
        """음수 금액 거부"""
        with self.assertRaises(ValueError):
            Transaction(
                date=date(2024, 1, 15),
                type="지출",
                category="식비",
                description="점심",
                amount=-1000,
            )

    def test_empty_category_defaults_to_기타(self):
        """빈 카테고리는 '기타'로 설정"""
        tx = Transaction(
            date=date(2024, 1, 15),
            type="지출",
            category="",
            description="점심",
            amount=10000,
        )
        self.assertEqual(tx.category, "기타")

    def test_to_dict(self):
        """dict 변환"""
        tx = Transaction(
            date=date(2024, 1, 15),
            type="지출",
            category="식비",
            description="점심",
            amount=10000,
        )

        data = tx.to_dict()

        self.assertIsInstance(data, dict)
        self.assertEqual(data["date"], date(2024, 1, 15))
        self.assertEqual(data["type"], "지출")
        self.assertEqual(data["amount"], 10000)

    def test_from_dict(self):
        """dict에서 생성"""
        data = {
            "date": date(2024, 1, 15),
            "type": "수입",
            "category": "월급",
            "description": "1월 급여",
            "amount": 3000000,
        }

        tx = Transaction.from_dict(data)

        self.assertEqual(tx.date, date(2024, 1, 15))
        self.assertEqual(tx.type, "수입")
        self.assertEqual(tx.category, "월급")
        self.assertEqual(tx.amount, 3000000)


class TestValidateTransactionDict(unittest.TestCase):
    """validate_transaction_dict 함수 테스트"""

    def test_valid_dict(self):
        """유효한 dict"""
        data = {
            "date": date(2024, 1, 15),
            "type": "지출",
            "category": "식비",
            "description": "점심",
            "amount": 10000,
        }
        self.assertTrue(validate_transaction_dict(data))

    def test_missing_keys(self):
        """필수 키 누락"""
        data = {
            "date": date(2024, 1, 15),
            "type": "지출",
            # category 누락
            "description": "점심",
            "amount": 10000,
        }
        self.assertFalse(validate_transaction_dict(data))

    def test_invalid_type(self):
        """잘못된 구분(type)"""
        data = {
            "date": date(2024, 1, 15),
            "type": "잘못된값",
            "category": "식비",
            "description": "점심",
            "amount": 10000,
        }
        self.assertFalse(validate_transaction_dict(data))

    def test_invalid_amount(self):
        """잘못된 금액"""
        data = {
            "date": date(2024, 1, 15),
            "type": "지출",
            "category": "식비",
            "description": "점심",
            "amount": -1000,
        }
        self.assertFalse(validate_transaction_dict(data))


if __name__ == "__main__":
    unittest.main()