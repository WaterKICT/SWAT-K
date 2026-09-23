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

    def test_valid_functions(self):
        """허용된 수학 함수(Sqrt, Pow, Log, Exp) 정상 동작 테스트"""
        valid_cases = [
            "Sqrt(v0) + Pow(v1, 2) + Log(v2) + Exp(v0)",
            "Pow(v0, 0.5) * (v1 + Log(v2, 10))",
            "Exp(v0) + Sqrt(v1 + v2)",
            "Pow(Sqrt(v0), 2) + Log(v1) + Exp(v2)",
            "Sqrt(v0) / Pow(v1, 3) + Log(Exp(v2))",
        ]
        for expr in valid_cases:
            with self.subTest(expr=expr):
                valid, msg = validate_formula(expr)
                self.assertTrue(valid, f"'{expr}'는 유효해야 합니다: {msg}")

    def test_case_sensitive_functions_rejected(self):
        """함수 대소문자 불일치 거부 테스트 (소문자 및 전체 대문자 거부)"""
        invalid_cases = [
            "sqrt(v0) + v1 + v2",
            "SQRT(v0) + v1 + v2",
            "pow(v0, 2) + v1 + v2",
            "POW(v0, 2) + v1 + v2",
            "log(v0) + v1 + v2",
            "LOG(v0) + v1 + v2",
            "exp(v0) + v1 + v2",
            "EXP(v0) + v1 + v2",
        ]
        for expr in invalid_cases:
            with self.subTest(expr=expr):
                valid, msg = validate_formula(expr)
                self.assertFalse(
                    valid, f"대소문자가 일치하지 않는 '{expr}'는 거부되어야 합니다."
                )

    def test_function_argument_count(self):
        """함수 인자 개수 불일치 거부 테스트"""
        invalid_cases = [
            "Sqrt() + v0 + v1 + v2",
            "Sqrt(v0, v1) + v2",
            "Pow(v0) + v1 + v2",
            "Pow(v0, v1, v2)",
            "Log() + v0 + v1 + v2",
            "Log(v0, v1, v2)",
            "Exp() + v0 + v1 + v2",
            "Exp(v0, v1) + v2",
        ]
        for expr in invalid_cases:
            with self.subTest(expr=expr):
                valid, msg = validate_formula(expr)
                self.assertFalse(
                    valid, f"인자 개수가 잘못된 '{expr}'는 거부되어야 합니다."
                )

    def test_bare_function_identifier_rejected(self):
        """함수가 호출 형태()가 아닌 변수처럼 사용된 경우 거부 테스트"""
        invalid_cases = [
            "v0 + Sqrt + v1 + v2",
            "v0 + Pow + v1 + v2",
            "v0 + Log + v1 + v2",
            "v0 + Exp + v1 + v2",
        ]
        for expr in invalid_cases:
            with self.subTest(expr=expr):
                valid, _ = validate_formula(expr)
                self.assertFalse(
                    valid, f"함수가 변수 위치에 사용된 '{expr}'는 거부되어야 합니다."
                )

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
