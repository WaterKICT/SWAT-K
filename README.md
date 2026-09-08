# SWAT-K (KICT SWAT PoC 2025)

SWAT(Soil and Water Assessment Tool) 데이터 처리, 변환 및 시각화를 위한 QGIS 플러그인입니다.

## 주요 기능

- **[SWAT-K] Run**
  - SWAT-K Converter 실행 파일(`.exe`) 및 RCH, CIO 파일 경로 지정
  - 시작 연도 설정 및 `QSettings` 기반 사용자 설정 자동 저장/복원
- **[SWAT-K] View**
  - **일단위 유량 차트**: 일별 유량 시계열(m³/s) 시각화
  - **소유역별 연도별 유황곡선**: 일수(Day)에 따른 유량을 로그 스케일로 표시
  - **홍수량 분석**: 연중 최대 유량을 바탕으로 최대홍수량 및 첨두홍수량 자동 산출
  - **차트 저장**: 고해상도(300 DPI) 이미지 파일 내보내기

## 설치 및 개발 환경

### 의존성 설치

```bash
# 의존성 설치
uv sync

# 개발 의존성 포함
uv sync --group dev
```

### QGIS 플러그인 로컬 로드

개발 중인 플러그인을 QGIS에 연동하려면 `src/swat_k` 디렉토리를 QGIS 플러그인 디렉토리에 심볼릭 링크하거나 복사합니다.

- **Windows QGIS 플러그인 경로**:
  `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\swat_k`

심볼릭 링크 생성 예시 (PowerShell 관리자 권한):
```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\swat_k" -Target "$PWD\src\swat_k"
```

이후 QGIS의 **플러그인 > 플러그인 관리 및 설치**에서 `SWAT-K`를 활성화하면 툴바에 `[SWAT-K] Run` 및 `[SWAT-K] View` 아이콘이 표시됩니다.

## 코드 품질 관리

```bash
# 린트 검사
uv run ruff check src

# 코드 포맷팅
uv run ruff format src
```

## 프로젝트 구조

```
swat-k/
├── .github/workflows/
│   └── release.yml          # GitHub Actions QGIS 플러그인 자동 릴리즈
├── data/                    # 샘플 데이터 (RCH, FlowDuration CSV)
├── src/
│   └── swat_k/
│       ├── __init__.py      # QGIS 플러그인 엔트리포인트 (classFactory)
│       ├── plugin.py        # QGIS 툴바 액션 등록 및 대화상자 제어
│       ├── run_window.py    # [SWAT-K] Run 대화상자 (Converter 실행 및 설정)
│       ├── view_window.py   # [SWAT-K] View 대화상자 (유량 차트 및 통계 분석)
│       ├── core/            # 비즈니스 로직
│       ├── utils/
│       │   └── settings.py  # QSettings 기반 설정 영속성 관리
│       ├── metadata.txt     # QGIS 플러그인 메타데이터
│       ├── icon_run.svg     # Run 툴바 아이콘
│       └── icon_view.svg    # View 툴바 아이콘
├── pyproject.toml           # 패키지 명세 및 Ruff/QGIS CI 설정
└── README.md
```