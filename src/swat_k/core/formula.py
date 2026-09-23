"""사용자 정의 수식 검증 및 처리 모듈"""

import ast
import re

DEFAULT_FORMULA = "0.5 * v0 + 0.5 * v2 + (2 * v1 - v0 - v2) /2"
REQUIRED_VARIABLES = ("v0", "v1", "v2")
ALLOWED_FUNCTIONS = {
    "Sqrt": (1,),
    "Pow": (2,),
    "Log": (1, 2),
    "Exp": (1,),
}

ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)


class FormulaValidator(ast.NodeVisitor):
    """수식 AST 구조의 안전성과 유효성을 검증하는 방문자 클래스"""

    def __init__(
        self,
        allowed_funcs: dict[str, tuple[int, ...]],
        allowed_vars: tuple[str, ...],
    ):
        self.allowed_funcs = allowed_funcs
        self.allowed_vars = set(allowed_vars)
        self.found_vars: set[str] = set()
        self.error: str | None = None

    def visit_Expression(self, node: ast.Expression) -> None:
        self.visit(node.body)

    def visit_Call(self, node: ast.Call) -> None:
        if self.error:
            return

        if not isinstance(node.func, ast.Name):
            self.error = "함수 호출 형식이 올바르지 않습니다."
            return

        func_name = node.func.id
        if func_name not in self.allowed_funcs:
            self.error = f"허용되지 않는 함수 '{func_name}'입니다."
            return

        if node.keywords:
            self.error = "함수에 키워드 인자를 사용할 수 없습니다."
            return

        expected_counts = self.allowed_funcs[func_name]
        arg_count = len(node.args)
        if arg_count not in expected_counts:
            expected_str = " 또는 ".join(str(c) for c in expected_counts)
            self.error = (
                f"함수 '{func_name}'의 인자 개수는 {expected_str}개여야 합니다 "
                f"(현재 {arg_count}개)."
            )
            return

        for arg in node.args:
            self.visit(arg)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if self.error:
            return

        if not isinstance(node.op, ALLOWED_BIN_OPS):
            self.error = "사칙연산(+, -, *, /) 이외의 연산자는 사용할 수 없습니다."
            return

        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if self.error:
            return

        if not isinstance(node.op, ALLOWED_UNARY_OPS):
            self.error = "지원되지 않는 단항 연산자가 포함되어 있습니다."
            return

        self.visit(node.operand)

    def visit_Constant(self, node: ast.Constant) -> None:
        if self.error:
            return

        if not isinstance(node.value, (int, float)):
            self.error = "수식에는 숫자 상수만 사용할 수 있습니다."

    def visit_Name(self, node: ast.Name) -> None:
        if self.error:
            return

        if node.id in self.allowed_vars:
            self.found_vars.add(node.id)
        else:
            self.error = f"허용되지 않는 식별자 '{node.id}'가 포함되어 있습니다."

    def generic_visit(self, node: ast.AST) -> None:
        if self.error:
            return
        self.error = (
            f"수식에 허용되지 않는 구문 요소({type(node).__name__})가 "
            "포함되어 있습니다."
        )


def validate_formula(formula: str) -> tuple[bool, str]:
    """사용자 정의 수식의 유효성을 검증합니다.

    검증 규칙:
    1. v0, v1, v2 변수가 모두 반드시 포함되어야 함 (소문자 필수, V0 등 대문자 불허)
    2. 허용되는 함수: Sqrt(1개), Pow(2개), Log(1~2개), Exp(1개) (대소문자 엄격 구분)
    3. 허용되는 문자: 변수(v0, v1, v2), 함수, 숫자, 사칙연산자(+, -, *, /),
       괄호((, )), 쉼표(,), 소수점(.), 공백
    4. ^, **(거듭제곱) 및 기타 특수문자/함수/알파벳 거부 (거듭제곱은 Pow 함수 사용)
    5. 괄호 쌍 불일치 및 연산자 누락 등 수식 문법(Syntax) 정합성 검사

    Args:
        formula: 검증할 수식 문자열

    Returns:
        (성공 여부, 오류 메시지). 유효한 경우 (True, "") 반환.
    """
    if not formula or not formula.strip():
        return False, "사용자 정의 식을 입력해주세요."

    raw = formula.strip()

    # 1. ^ 및 ** 기호 명시적 거부
    if "^" in raw:
        return (
            False,
            "'^' 기호는 지원하지 않습니다. "
            "거듭제곱은 Pow(밑, 지수) 함수를 사용해주세요.",
        )
    if "**" in raw:
        return (
            False,
            "'**' 기호는 지원하지 않습니다. "
            "거듭제곱은 Pow(밑, 지수) 함수를 사용해주세요.",
        )

    # 2. 필수 변수(v0, v1, v2) 소문자 존재 여부 검사
    for var in REQUIRED_VARIABLES:
        if not re.search(rf"\b{var}\b", raw):
            return (
                False,
                f"수식에 '{var}' 변수가 반드시 포함되어야 합니다. (소문자만 허용)",
            )

    # 3. 허용 식별자(v0, v1, v2, Sqrt, Pow, Log, Exp) 외
    #    다른 영문 식별자/변수/함수 사용 여부 검사
    allowed_ids_pattern = r"\b(v0|v1|v2|Sqrt|Pow|Log|Exp)\b"
    stripped_ids = re.sub(allowed_ids_pattern, "", raw)
    if re.search(r"[a-zA-Z_]", stripped_ids):
        return (
            False,
            "수식에는 허용된 변수(v0, v1, v2) 및 함수(Sqrt, Pow, Log, Exp) 외의 "
            "다른 문자나 식별자(대소문자 불일치 포함)를 사용할 수 없습니다.",
        )

    # 4. 허용된 문자(숫자, 사칙연산자, 괄호, 쉼표, 공백, 소수점) 이외의 특수문자 검사
    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.,]*", stripped_ids):
        return (
            False,
            "수식에는 변수, 함수, 숫자, 사칙연산자(+, -, *, /), 괄호, 쉼표(,)만 "
            "사용할 수 있습니다.",
        )

    # 5. 파이썬 AST 파싱을 통한 문법(Syntax) 검증
    try:
        tree = ast.parse(raw, mode="eval")
    except SyntaxError as e:
        return False, f"수식의 문법이 올바르지 않습니다: {e.msg}"

    # 6. AST 구조 및 안전성 검증
    validator = FormulaValidator(ALLOWED_FUNCTIONS, REQUIRED_VARIABLES)
    validator.visit(tree)

    if validator.error:
        return False, validator.error

    # 7. 세 변수가 모두 식의 피연산자로 파싱되었는지 최종 확인
    for var in REQUIRED_VARIABLES:
        if var not in validator.found_vars:
            return (
                False,
                f"수식에 '{var}' 변수가 올바르게 포함되어야 합니다.",
            )

    return True, ""
