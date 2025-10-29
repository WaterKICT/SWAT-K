# KICT SWAT PoC 2025

SWAT 데이터 처리 및 시각화 도구

## 기능

- RCH 및 CIO 파일 입력
- SWAT 데이터 변환
- 일단위 유량 차트
- 소유역별 유황곡선
- 최대홍수량 및 첨두홍수량 계산

## 설치

```bash
# 의존성 설치
uv sync

# 개발 의존성 포함
uv sync --group dev
```

## 실행

```bash
# uv를 통해 실행
uv run swat-k

# 또는 개발 모드로 실행
uv run python -m swat_k.main
```

## 개발

```bash
# UI 파일 수정 후 Python 코드로 변환
uv run pyside6-uic output.ui -o src/swat_k/ui/output_ui.py

# 코드 검사
uv run ruff check .

# 코드 포맷팅
uv run ruff format .
```

## 프로젝트 구조

```
swat-k/
├── src/
│   └── swat_k/
│       ├── __init__.py
│       ├── main.py              # 엔트리 포인트
│       ├── main_window.py       # 메인 윈도우 클래스
│       ├── ui/
│       │   ├── __init__.py
│       │   └── output_ui.py     # UI 변환 파일
│       ├── core/                # 비즈니스 로직
│       │   └── __init__.py
│       └── utils/               # 유틸리티
│           └── __init__.py
├── output.ui                     # Qt Designer UI 파일
├── pyproject.toml
└── README.md
```