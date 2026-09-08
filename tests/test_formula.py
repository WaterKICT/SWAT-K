"""사용자 정의 수식 유효성 검증 단위 테스트"""

import unittest

from swat_k.core.formula import DEFAULT_FORMULA, validate_formula


class TestFormulaValidation(unittest.TestCase):
    """사용자 정의 식 검증 규칙 테스트"""

    def test_default_formula(self):
        """기본 수식 검증"""
        valid, msg = validate_formula(DEFAULT_FORMULA)
        self.assertTrue(valid, f"기본 수식이 유효해야 합니다: {msg}")
        self.assertEqual(msg, "")

    def test_valid_custom_formulas(self):
        """유효한 사용자 정의 수식 테스트"""
        test_cases = [
            "v0 + v1 + v2",
            "(v0 + v1) * 2 - v2 / 4",
            "0.1 * v0 + 0.2 * v1 + 0.7 * v2",
            "(2 * v0 - (v1 + v2)) / 3.5",
            "-v0 + +v1 - (-v2)",
        ]
        for expr in test_cases:
            with self.subTest(expr=expr):
                valid, msg = validate_formula(expr)
                self.assertTrue(valid, f"'{expr}'는 유효해야 합니다: {msg}")

    def test_missing_variables(self):
        """변수(v0, v1, v2) 누락 테스트"""
        # v2 누락
        valid, msg = validate_formula("v0 + v1")
        self.assertFalse(valid)
        self.assertIn("v2", msg)

        # v0 누락
        valid, msg = validate_formula("v1 + v2")
        self.assertFalse(valid)
        self.assertIn("v0", msg)

        # v1 누락
        valid, msg = validate_formula("v0 + v2")
        self.assertFalse(valid)
        self.assertIn("v1", msg)

    def test_uppercase_variables_rejected(self):
        """대문자 변수(V0, V1, V2) 거부 테스트"""
        test_cases = [
            "V0 + v1 + v2",
            "v0 + V1 + v2",
            "v0 + v1 + V2",
            "v0 + v1 + v2 + V0",
        ]
        for expr in test_cases:
            with self.subTest(expr=expr):
                valid, msg = validate_formula(expr)
                self.assertFalse(
                    valid, f"대문자가 포함된 '{expr}'는 거부되어야 합니다."
                )

    def test_caret_rejected(self):
        """^ 기호 거부 테스트"""
        valid, msg = validate_formula("v0^2 + v1 + v2")
        self.assertFalse(valid)
        self.assertIn("^", msg)

    def test_power_operator_rejected(self):
        """** 연산자 거부 테스트"""
        valid, msg = validate_formula("v0**2 + v1 + v2")
        self.assertFalse(valid)

    def test_forbidden_characters_and_identifiers(self):
        """허용되지 않는 문자 및 식별자 테스트"""
        invalid_cases = [
            "v0 + v1 + v2 + a",
            "v0 + v1 + v2 + x",
            "v01 + v1 + v2",
            "v0 + v20 + v1",
            "_v0 + v1 + v2",
            "v0 + v1 + v2 % 2",
            "v0 + v1 + v2 & 1",
            "sin(v0) + v1 + v2",
            "v0 + v1 + v2; import os",
        ]
        for expr in invalid_cases:
            with self.subTest(expr=expr):
                valid, _ = validate_formula(expr)
                self.assertFalse(valid, f"'{expr}'는 거부되어야 합니다.")

    def test_syntax_errors(self):
        """구문 문법 오류 테스트"""
        syntax_err_cases = [
            "v0 + v1 + v2 +",
            "(v0 + v1 + v2",
            "v0 + (v1 + v2))",
            "v0 v1 v2",
            "",
            "   ",
        ]
        for expr in syntax_err_cases:
            with self.subTest(expr=expr):
                valid, _ = validate_formula(expr)
                self.assertFalse(valid, f"문법 오류 '{expr}'는 거부되어야 합니다.")


if __name__ == "__main__":
    unittest.main()
