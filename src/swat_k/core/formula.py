"""사용자 정의 수식 검증 및 처리 모듈"""

import ast
import re

DEFAULT_FORMULA = "0.5 * v0 + 0.5 * v2 + (2 * v1 - v0 - v2) /2"
REQUIRED_VARIABLES = ("v0", "v1", "v2")

ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)


def validate_formula(formula: str) -> tuple[bool, str]:
    """사용자 정의 수식의 유효성을 검증합니다.

    검증 규칙:
    1. v0, v1, v2 변수가 모두 반드시 포함되어야 함 (소문자 필수, V0 등 대문자 불허)
    2. 허용되는 문자: 변수(v0, v1, v2), 숫자, 사칙연산자(+, -, *, /), 괄호((, )), 공백
    3. ^, **(거듭제곱) 및 기타 특수문자/함수/알파벳 거부
    4. 괄호 쌍 불일치 및 연산자 누락 등 수식 문법(Syntax) 정합성 검사

    Args:
        formula: 검증할 수식 문자열

    Returns:
        (성공 여부, 오류 메시지). 유효한 경우 (True, "") 반환.
    """
    if not formula or not formula.strip():
        return False, "사용자 정의 식을 입력해주세요."

    raw = formula.strip()

    # 1. ^ 기호 명시적 거부
    if "^" in raw:
        return (
            False,
            "'^' 기호는 지원하지 않습니다. "
            "괄호와 사칙연산자(+, -, *, /)를 사용해주세요.",
        )

    # 2. 필수 변수(v0, v1, v2) 소문자 존재 여부 검사
    for var in REQUIRED_VARIABLES:
        # 단어 경계(\b)를 사용하여 v0, v1, v2 정확히 매칭
        if not re.search(rf"\b{var}\b", raw):
            return (
                False,
                f"수식에 '{var}' 변수가 반드시 포함되어야 합니다. (소문자만 허용)",
            )

    # 3. 대문자 V0, V1, V2 또는 다른 알파벳 변수 사용 여부 검사
    # v0, v1, v2를 일시적으로 제거한 뒤 남은 문자열에 알파벳이 있는지 검사
    stripped_vars = re.sub(r"\bv[012]\b", "", raw)
    if re.search(r"[a-zA-Z_]", stripped_vars):
        return (
            False,
            "수식에는 v0, v1, v2 변수 외의 다른 문자나 변수(대문자 포함)를 "
            "사용할 수 없습니다.",
        )

    # 4. 허용된 문자(숫자, 사칙연산자, 괄호, 공백, 소수점) 이외의 특수문자 검사
    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.]*", stripped_vars):
        return (
            False,
            "수식에는 변수(v0, v1, v2), 숫자, 사칙연산자(+, -, *, /), 괄호만 "
            "사용할 수 있습니다.",
        )

    # 5. 파이썬 AST 파싱을 통한 문법(Syntax) 및 안전성 검증
    try:
        tree = ast.parse(raw, mode="eval")
    except SyntaxError as e:
        return False, f"수식의 문법이 올바르지 않습니다: {e.msg}"

    # 6. AST 노드 순회를 통해 허용되지 않는 연산(예: ** 거듭제곱, 함수 호출 등) 차단
    found_vars = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Expression, ast.Load, *ALLOWED_BIN_OPS, *ALLOWED_UNARY_OPS)
        ):
            continue
        elif isinstance(node, ast.BinOp):
            if not isinstance(node.op, ALLOWED_BIN_OPS):
                return (
                    False,
                    "사칙연산(+, -, *, /) 이외의 연산자(예: 거듭제곱 등)는 "
                    "사용할 수 없습니다.",
                )
        elif isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, ALLOWED_UNARY_OPS):
                return False, "지원되지 않는 단항 연산자가 포함되어 있습니다."
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                return False, "수식에는 숫자 상수만 사용할 수 있습니다."
        elif isinstance(node, ast.Name):
            if node.id not in REQUIRED_VARIABLES:
                return False, f"허용되지 않는 변수 '{node.id}'가 포함되어 있습니다."
            found_vars.add(node.id)
        else:
            return (
                False,
                f"수식에 허용되지 않는 구문 요소({type(node).__name__})가 "
                "포함되어 있습니다.",
            )

    # AST 상에서도 세 변수가 모두 식의 피연산자로 파싱되었는지 최종 확인
    for var in REQUIRED_VARIABLES:
        if var not in found_vars:
            return (
                False,
                f"수식에 '{var}' 변수가 올바르게 포함되어야 합니다.",
            )

    return True, ""
