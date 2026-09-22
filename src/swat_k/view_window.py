"""[SWAT-K] View 시각화 대화상자 모듈"""

import re
from datetime import datetime
from pathlib import Path

import matplotlib
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from swat_k.core.gis_visualizer import (
    SubbasinSelectMapTool,
    detect_reach_id_field,
    get_layer_by_name_or_id,
    get_layer_fields,
    get_qgis_vector_layers,
    highlight_subbasin_feature,
)
from swat_k.utils import settings
from swat_k.utils.logger import (
    log_error,
    log_warning,
    show_error_message,
)

try:
    from qgis.PyQt.QtCore import Qt, pyqtSlot
    from qgis.PyQt.QtWidgets import (
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide6.QtCore import Qt
    from PySide6.QtCore import Slot as pyqtSlot
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False


def get_month_first_days(
    year: int = 2020, one_indexed: bool = False
) -> tuple[list[int], list[str]]:
    """지정된 연도의 매월 1일에 해당하는 Day 인덱스와 라벨('1월' 등) 목록을 반환합니다.

    Args:
        year: 대상 연도 (윤년 여부 판정용)
        one_indexed: 1-indexed 여부 (유황곡선처럼 1부터 시작하는 경우 True)

    Returns:
        (ticks, labels) 튜플
    """
    ticks = []
    labels = []
    valid_year = year if isinstance(year, int) and year > 0 else 2020
    for month in range(1, 13):
        dt = datetime(valid_year, month, 1)
        yday = dt.timetuple().tm_yday
        tick = yday if one_indexed else (yday - 1)
        ticks.append(tick)
        labels.append(f"{month}월")
    return ticks, labels


def find_latest_out_dir(base_dir: Path | str) -> Path | None:
    """rch 파일 디렉토리 등에서 가장 최근 생성된 out_timestamp 디렉토리를 탐색합니다."""
    if not base_dir:
        return None
    p = Path(base_dir)
    if not p.is_dir():
        return None
    out_dirs = [d for d in p.glob("out_*") if d.is_dir()]
    if not out_dirs:
        return None
    return sorted(out_dirs, key=lambda d: (d.name, d.stat().st_mtime), reverse=True)[0]


def resolve_effective_data_dir(data_dir: Path | str) -> Path:
    """최신 out_timestamp 결과 폴더가 있으면 해당 폴더를 반환합니다."""
    if not data_dir:
        return Path(".")
    p = Path(data_dir)
    if not p.is_dir():
        return p
    latest_out = find_latest_out_dir(p)
    if latest_out and any(latest_out.glob("*.csv")):
        return latest_out
    return p


def find_flow_duration_file(
    data_dir: Path, rch_path: str = "", reach_id: int = 1
) -> Path | None:
    """데이터 디렉토리에서 특정 소유역(reach_id)의 FlowDuration CSV 파일을 탐색합니다.

    Args:
        data_dir: Swat-K 전용 데이터 폴더 경로
        rch_path: RCH 파일 경로 (선택)
        reach_id: 대상 소유역 번호 (기본값: 1)

    Returns:
        탐색된 FlowDuration CSV의 Path 객체 또는 None
    """
    if not data_dir or not data_dir.is_dir():
        return None

    eff_dir = resolve_effective_data_dir(data_dir)
    rch_name = Path(rch_path).name if rch_path else ""
    rch_stem = Path(rch_path).stem if rch_path else ""

    candidates = [
        eff_dir / f"FlowDuration_{reach_id}.csv",
        eff_dir / "FlowDuration.csv" if reach_id == 1 else None,
    ]
    if rch_name:
        candidates.extend(
            [
                eff_dir / f"{rch_name}_FlowDuration_{reach_id}.csv",
                eff_dir / f"{rch_name}_FlowDuration.csv" if reach_id == 1 else None,
            ]
        )
    if rch_stem:
        candidates.extend(
            [
                eff_dir / f"{rch_stem}_FlowDuration_{reach_id}.csv",
                eff_dir / f"{rch_stem}_FlowDuration.csv" if reach_id == 1 else None,
            ]
        )

    for c in candidates:
        if c and c.is_file():
            return c

    # 와일드카드 패턴 검색 (*_FlowDuration_{reach_id}.csv 등)
    patterns = [
        f"*_FlowDuration_{reach_id}.csv",
        f"*FlowDuration_{reach_id}.csv",
    ]
    if reach_id == 1:
        patterns.extend(
            [
                "*_FlowDuration.csv",
                "*FlowDuration.csv",
                "*_FlowDuration*.csv",
                "*FlowDuration*.csv",
            ]
        )

    for pattern in patterns:
        matched = sorted(eff_dir.glob(pattern))
        if matched:
            return matched[0]

    return None


def extract_years_from_flow_duration(csv_path: Path | str) -> list[str]:
    """FlowDuration CSV의 첫 번째 헤더 행에서 연도 목록을 추출합니다.

    Args:
        csv_path: FlowDuration CSV 파일 경로

    Returns:
        연도 문자열 목록 (예: ['2013', '2014', ...])
    """
    p = Path(csv_path) if csv_path else None
    if not p or not p.is_file():
        return []
    try:
        with open(p, encoding="utf-8", errors="ignore") as f:
            header = f.readline().strip()
        years = []
        for token in header.split(","):
            token = token.strip()
            if token.isdigit() and len(token) == 4:
                years.append(token)
        return years
    except Exception:
        return []


def find_daily_flow_file(
    data_dir: Path, rch_path: str = "", reach_id: int = 1
) -> Path | None:
    """데이터 디렉토리에서 특정 소유역(reach_id)의 일단위 유량 CSV 파일을 탐색합니다.

    Args:
        data_dir: Swat-K 전용 데이터 폴더 경로
        rch_path: RCH 파일 경로 (선택)
        reach_id: 대상 소유역 번호 (기본값: 1)

    Returns:
        탐색된 일별 유량 CSV의 Path 객체 또는 None
    """
    if not data_dir or not data_dir.is_dir():
        return None

    eff_dir = resolve_effective_data_dir(data_dir)
    rch_name = Path(rch_path).name if rch_path else ""
    rch_stem = Path(rch_path).stem if rch_path else ""

    candidates = [
        eff_dir / f"{reach_id}.csv",
    ]
    if (
        rch_path
        and Path(rch_path).is_file()
        and Path(rch_path).suffix.lower() == ".csv"
        and reach_id == 1
    ):
        candidates.append(Path(rch_path))

    if rch_name:
        candidates.extend(
            [
                eff_dir / f"{rch_name}_{reach_id}.csv",
                eff_dir / f"{rch_name}.csv" if reach_id == 1 else None,
            ]
        )
    if rch_stem:
        candidates.extend(
            [
                eff_dir / f"{rch_stem}_{reach_id}.csv",
                eff_dir / f"{rch_stem}.csv" if reach_id == 1 else None,
            ]
        )

    for c in candidates:
        if c and c.is_file():
            return c

    # 와일드카드 패턴 검색 (*_{reach_id}.csv 등, 단 FlowDuration이나 Max 제외)
    matched = sorted(eff_dir.glob(f"*_{reach_id}.csv"))
    valid = [
        f
        for f in matched
        if not any(k in f.name for k in ["FlowDuration", "Max_step", "all"])
    ]
    if valid:
        return valid[0]

    # all.csv 또는 _all.csv 확인 (전체 reach가 통합된 파일)
    if (eff_dir / "all.csv").is_file():
        return eff_dir / "all.csv"
    all_matched = sorted(eff_dir.glob("*_all.csv"))
    if all_matched:
        return all_matched[0]
    all_matched_alt = sorted(eff_dir.glob("*all.csv"))
    if all_matched_alt:
        return all_matched_alt[0]

    return None


def find_available_reaches(data_dir: Path, rch_path: str = "") -> list[int]:
    """데이터 디렉토리에서 사용 가능한 소유역(Reach) 번호 목록을 탐색합니다.

    Args:
        data_dir: Swat-K 전용 데이터 폴더 경로
        rch_path: RCH 파일 경로 (선택)

    Returns:
        정렬된 소유역 번호 리스트 (예: [1, 2, ..., 12])
    """
    if not data_dir or not data_dir.is_dir():
        return [1]

    eff_dir = resolve_effective_data_dir(data_dir)
    reaches = set()

    # 1. all.csv 및 *_all.csv 헤더 확인
    all_files = []
    if (eff_dir / "all.csv").is_file():
        all_files.append(eff_dir / "all.csv")
    for f in eff_dir.glob("*all.csv"):
        if f not in all_files:
            all_files.append(f)

    for f in all_files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fp:
                line = fp.readline()
            for token in line.split(","):
                token = token.strip()
                if token.isdigit():
                    reaches.add(int(token))
        except (OSError, UnicodeError) as e:
            log_warning(f"소유역 번호 파일({f.name}) 읽기 실패: {e}")
        except Exception as e:
            log_warning(f"소유역 번호 파싱 중 예외 발생({f.name}): {e}")

    # 2. FlowDuration_*.csv 및 *_FlowDuration_*.csv 패턴 확인
    for f in eff_dir.glob("*FlowDuration_*.csv"):
        m = re.search(r"(?:^|_)FlowDuration_(\d+)\.csv$", f.name)
        if m:
            reaches.add(int(m.group(1)))

    # 3. 개별 하천 시계열 파일 ({id}.csv 및 *_{id}.csv) 확인
    for f in eff_dir.glob("*.csv"):
        if any(k in f.name for k in ["FlowDuration", "Max_step", "all", "equation"]):
            continue
        if f.stem.isdigit():
            reaches.add(int(f.stem))
            continue
        m = re.search(r"_(\d+)\.csv$", f.name)
        if m:
            reaches.add(int(m.group(1)))

    return sorted(reaches) if reaches else [1]


def find_equation_file(data_dir: Path, rch_path: str = "") -> Path | None:
    """데이터 디렉토리에서 첨두홍수량 계산 수식이 저장된 Max_step3_equation.csv 파일을 탐색합니다.

    Args:
        data_dir: Swat-K 전용 데이터 폴더 경로
        rch_path: RCH 파일 경로 (선택)

    Returns:
        탐색된 수식 CSV의 Path 객체 또는 None
    """
    if not data_dir or not data_dir.is_dir():
        return None

    eff_dir = resolve_effective_data_dir(data_dir)
    rch_name = Path(rch_path).name if rch_path else ""
    rch_stem = Path(rch_path).stem if rch_path else ""

    candidates = [
        eff_dir / "Max_step3_equation.csv",
    ]
    if rch_name:
        candidates.append(eff_dir / f"{rch_name}_Max_step3_equation.csv")
    if rch_stem:
        candidates.append(eff_dir / f"{rch_stem}_Max_step3_equation.csv")

    for c in candidates:
        if c and c.is_file():
            return c

    # 와일드카드 패턴 검색 (*Max_step3_equation.csv 등)
    matched = sorted(eff_dir.glob("*Max_step3_equation.csv"))
    if matched:
        return matched[0]

    matched_alt = sorted(eff_dir.glob("*equation*.csv"))
    if matched_alt:
        return matched_alt[0]

    return None


def read_user_equation(csv_path: Path | str | None) -> str:
    """Max_step3_equation.csv 파일로부터 사용자 식 문자열을 읽어옵니다.

    Args:
        csv_path: 수식 파일 경로

    Returns:
        수식 문자열 (파일이 없거나 읽기 실패 시 빈 문자열)
    """
    if not csv_path:
        return ""
    p = Path(csv_path)
    if not p.is_file():
        return ""

    for enc in ["utf-8", "cp949", "euc-kr", "latin1"]:
        try:
            with open(p, encoding=enc, errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        return stripped
        except Exception:
            continue
    return ""


class ViewDialog(QDialog):
    """SWAT 데이터 차트 시각화 및 결과 조회 대화상자"""

    def __init__(self, parent=None, iface=None):
        super().__init__(parent)
        self.iface = iface
        self.map_tool = None
        self.setWindowTitle("[SWAT-K] View - 데이터 시각화")
        self.resize(880, 880)
        self.setMinimumSize(660, 560)

        self._init_ui()
        self._load_saved_settings()

        if self.iface:
            try:
                from qgis.core import QgsProject

                proj = QgsProject.instance()
                if proj:
                    proj.layersAdded.connect(self._populate_qgis_layers)
                    proj.layersRemoved.connect(self._populate_qgis_layers)
            except Exception as e:
                log_warning(f"QGIS 레이어 이벤트 연동 실패: {e}")

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. SWAT-K 전용 데이터 폴더 및 대상 연도/소유역 설정
        group_controls = QGroupBox("SWAT-K 데이터 및 대상 설정", self)
        layout_controls = QFormLayout(group_controls)
        layout_controls.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout_controls.setSpacing(8)

        # Swat-K 전용 데이터 폴더
        self.lineEdit_data_dir = QLineEdit(self)
        self.lineEdit_data_dir.setPlaceholderText("Swat-K 전용 데이터 폴더 경로")
        self.lineEdit_data_dir.editingFinished.connect(self._on_data_dir_edited)
        self.btn_browse_data_dir = QPushButton("찾아보기...", self)
        self.btn_browse_data_dir.clicked.connect(self._browse_data_dir)

        layout_data_dir = QHBoxLayout()
        layout_data_dir.addWidget(self.lineEdit_data_dir)
        layout_data_dir.addWidget(self.btn_browse_data_dir)
        layout_controls.addRow("Swat-K 전용 데이터 폴더:", layout_data_dir)

        # 대상 연도 선택 (Combo)
        self.combo_year = QComboBox(self)
        self.combo_year.setMinimumWidth(140)
        self.combo_year.currentTextChanged.connect(self._on_year_changed)

        self.btn_reload_years = QPushButton("새로고침", self)
        self.btn_reload_years.setToolTip(
            "데이터 폴더의 파일들로부터 소유역 및 연도 목록을 다시 불러옵니다."
        )
        self.btn_reload_years.clicked.connect(self._populate_controls_from_data_dir)

        layout_year = QHBoxLayout()
        layout_year.addWidget(self.combo_year)
        layout_year.addWidget(self.btn_reload_years)
        layout_year.addStretch()
        layout_controls.addRow("대상 연도 선택:", layout_year)

        # QGIS 소유역 레이어 선택 (Combo + 새로고침 버튼)
        self.combo_layer = QComboBox(self)
        self.combo_layer.setMinimumWidth(200)
        self.combo_layer.currentTextChanged.connect(self._on_layer_changed)

        self.btn_refresh_layers = QPushButton("레이어 새로고침", self)
        self.btn_refresh_layers.setToolTip(
            "QGIS 프로젝트에 로드된 벡터 레이어 목록을 다시 검색합니다."
        )
        self.btn_refresh_layers.clicked.connect(self._populate_qgis_layers)

        layout_layer = QHBoxLayout()
        layout_layer.addWidget(self.combo_layer)
        layout_layer.addWidget(self.btn_refresh_layers)
        layout_layer.addStretch()
        layout_controls.addRow("QGIS 소유역 레이어:", layout_layer)

        # 소유역(Reach) 필드 선택 (Combo)
        self.combo_field = QComboBox(self)
        self.combo_field.setMinimumWidth(200)
        self.combo_field.currentTextChanged.connect(self._on_field_changed)

        layout_field = QHBoxLayout()
        layout_field.addWidget(self.combo_field)
        layout_field.addStretch()
        layout_controls.addRow("소유역(Reach) 필드:", layout_field)

        # 대상 소유역 선택 (Combo + 지도에서 마우스로 선택 버튼)
        self.combo_reach = QComboBox(self)
        self.combo_reach.setMinimumWidth(140)
        self.combo_reach.currentTextChanged.connect(self._on_reach_combo_changed)

        self.btn_select_on_map = QPushButton("지도에서 마우스로 선택", self)
        self.btn_select_on_map.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #EEF2FF; "
            "color: #4338CA; border: 1px solid #C7D2FE; border-radius: 4px; "
            "padding: 4px 12px; }\n"
            "QPushButton:hover { background-color: #E0E7FF; }"
        )
        self.btn_select_on_map.setToolTip(
            "QGIS 지도에서 마우스 클릭으로 소유역을 직접 선택합니다."
        )
        self.btn_select_on_map.clicked.connect(self._activate_map_select_tool)

        layout_reach = QHBoxLayout()
        layout_reach.addWidget(self.combo_reach)
        layout_reach.addWidget(self.btn_select_on_map)
        layout_reach.addStretch()
        layout_controls.addRow("대상 소유역 선택:", layout_reach)

        root_layout.addWidget(group_controls)

        # 2. 명시적 대상 정보 표시 배너 (Status Banner)
        self.banner_frame = QFrame(self)
        self.banner_frame.setStyleSheet(
            "QFrame {"
            "  background-color: #EFF6FF;"
            "  border: 1px solid #93C5FD;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "}"
        )
        layout_banner = QHBoxLayout(self.banner_frame)
        layout_banner.setContentsMargins(4, 4, 4, 4)

        self.label_banner = QLabel(
            "현재 조회 대상: [ -번 소유역  |  - 년 ]", self.banner_frame
        )
        self.label_banner.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1E40AF;"
        )
        layout_banner.addWidget(self.label_banner)
        layout_banner.addStretch()

        self.label_equation = QLabel("사용자 식: -", self.banner_frame)
        self.label_equation.setStyleSheet(
            "QLabel {"
            "  font-size: 12px; font-weight: bold; color: #1E3A8A;"
            "  background-color: #DBEAFE; border: 1px solid #BFDBFE;"
            "  border-radius: 4px; padding: 3px 10px;"
            "}"
        )
        self.label_equation.setToolTip(
            "첨두홍수량 계산에 적용된 수식 (Max_step3_equation.csv)"
        )
        layout_banner.addWidget(self.label_equation)

        root_layout.addWidget(self.banner_frame)

        # 3. 스크롤 영역 (차트 2개 및 통계 결과)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(4, 4, 4, 4)

        # 일단위 유량 차트
        group_daily = QGroupBox("일단위 유량 차트", container)
        layout_daily = QVBoxLayout(group_daily)
        self.fig_daily = Figure(figsize=(8, 3.5), tight_layout=True)
        self.ax_daily = self.fig_daily.add_subplot(111)
        self._format_daily_axes()
        self.canvas_daily = FigureCanvas(self.fig_daily)
        self.canvas_daily.setMinimumHeight(240)
        self.canvas_daily.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout_daily.addWidget(self.canvas_daily)
        content_layout.addWidget(group_daily)

        # 소유역별 연도별 유황곡선
        group_duration = QGroupBox("소유역별 연도별 유황곡선", container)
        layout_duration = QVBoxLayout(group_duration)
        self.fig_duration = Figure(figsize=(8, 3.5), tight_layout=True)
        self.ax_duration = self.fig_duration.add_subplot(111)
        self._format_duration_axes()
        self.canvas_duration = FigureCanvas(self.fig_duration)
        self.canvas_duration.setMinimumHeight(240)
        self.canvas_duration.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout_duration.addWidget(self.canvas_duration)
        content_layout.addWidget(group_duration)

        # 통계 결과 (최대홍수량 및 첨두홍수량)
        group_stats = QGroupBox("홍수량 분석 결과", container)
        layout_stats = QFormLayout(group_stats)
        layout_stats.setSpacing(8)

        self.label_max_flow_val = QLabel("-", group_stats)
        self.label_max_flow_val.setStyleSheet("font-weight: bold; color: #1E40AF;")
        layout_stats.addRow("최대홍수량 :", self.label_max_flow_val)

        self.label_peak_flow_val = QLabel("-", group_stats)
        self.label_peak_flow_val.setStyleSheet("font-weight: bold; color: #DC2626;")
        layout_stats.addRow("첨두홍수량 :", self.label_peak_flow_val)

        content_layout.addWidget(group_stats)

        scroll_area.setWidget(container)
        root_layout.addWidget(scroll_area, 1)

        # 4. 하단 액션 버튼
        bottom_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("차트 새로고침", self)
        self.btn_refresh.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 5px 16px; }"
        )
        self.btn_refresh.clicked.connect(self._render_data)

        self.btn_save_charts = QPushButton("차트 이미지 저장", self)
        self.btn_save_charts.clicked.connect(self._save_current_charts)
        self.btn_close = QPushButton("닫기", self)
        self.btn_close.clicked.connect(self.close)

        bottom_layout.addWidget(self.btn_refresh)
        bottom_layout.addWidget(self.btn_save_charts)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)
        root_layout.addLayout(bottom_layout)

    def _format_daily_axes(self, info_label="", year: int = 2020):
        title = f"일단위 유량 차트 {info_label}".strip()
        self.ax_daily.set_title(title, fontdict={"family": "Malgun Gothic"})
        self.ax_daily.set_xlabel("날짜", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.set_ylabel("유량 (m³/s)", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.grid(True, linestyle="--", alpha=0.5)
        ticks, labels = get_month_first_days(year, one_indexed=False)
        self.ax_daily.set_xticks(ticks)
        self.ax_daily.set_xticklabels(
            labels, fontdict={"family": "Malgun Gothic", "size": 8.5}
        )

    def _format_duration_axes(self, info_label=""):
        title = f"소유역별 연도별 유황곡선 {info_label}".strip()
        self.ax_duration.set_title(title, fontdict={"family": "Malgun Gothic"})
        self.ax_duration.set_xlabel("Day", fontdict={"family": "Malgun Gothic"})
        self.ax_duration.set_ylabel("유량 (m³/s)", fontdict={"family": "Malgun Gothic"})
        self.ax_duration.set_yscale("log")
        self.ax_duration.grid(True, which="both", linestyle="--", alpha=0.5)

    def _load_saved_settings(self):
        """저장된 설정 불러오기 및 UI 동기화"""
        saved_dir = settings.get_data_dir()
        if saved_dir:
            self.lineEdit_data_dir.setText(saved_dir)
        self._populate_controls_from_data_dir()
        self._populate_qgis_layers()

    def refresh_from_settings(self):
        """외부(예: Run 창 완료 후 또는 플러그인 메인)에서 설정 변경 시 UI 동기화"""
        current_text = self.lineEdit_data_dir.text().strip()
        saved_dir = settings.get_data_dir()
        if saved_dir and saved_dir != current_text:
            self.lineEdit_data_dir.setText(saved_dir)
        self._populate_controls_from_data_dir()
        self._populate_qgis_layers()

    def showEvent(self, event):
        """대화상자가 화면에 표시될 때 최신 설정 반영"""
        super().showEvent(event)
        self.refresh_from_settings()

    def closeEvent(self, event):
        """창 닫힐 때 맵 툴 해제 및 정리"""
        if self.iface and self.map_tool:
            try:
                canvas = self.iface.mapCanvas()
                if (
                    canvas
                    and hasattr(canvas, "mapTool")
                    and canvas.mapTool() == self.map_tool
                ):
                    canvas.unsetMapTool(self.map_tool)
            except Exception as e:
                log_warning(f"맵 툴 해제 중 예외 발생: {e}")
        super().closeEvent(event)

    def _get_current_reach_id(self) -> int:
        """현재 콤보박스에 선택된 소유역 번호 반환"""
        text = self.combo_reach.currentText()
        m = re.search(r"(\d+)", text)
        if m:
            return int(m.group(1))
        return settings.get_target_reach()

    @pyqtSlot()
    def _browse_data_dir(self):
        """Swat-K 전용 데이터 폴더 선택 대화상자"""
        current_dir = self.lineEdit_data_dir.text().strip()
        if not current_dir or not Path(current_dir).is_dir():
            rch_path = settings.get_rch_path()
            if rch_path and Path(rch_path).parent.is_dir():
                current_dir = str(Path(rch_path).parent)
            else:
                current_dir = ""

        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Swat-K 전용 데이터 폴더 선택",
            current_dir,
        )
        if selected_dir:
            self.lineEdit_data_dir.setText(selected_dir)
            settings.set_data_dir(selected_dir)
            self._populate_controls_from_data_dir()

    @pyqtSlot()
    def _on_data_dir_edited(self):
        """사용자가 LineEdit에서 폴더 경로를 직접 입력/수정 완료했을 때"""
        dir_text = self.lineEdit_data_dir.text().strip()
        if dir_text and Path(dir_text).is_dir():
            settings.set_data_dir(dir_text)
            self._populate_controls_from_data_dir()

    @pyqtSlot()
    def _populate_qgis_layers(self):
        """QGIS 프로젝트에 로드된 유효한 벡터 레이어 목록을 콤보박스에 반영합니다."""
        layers = get_qgis_vector_layers()
        saved_layer = settings.get_selected_layer_name()

        self.combo_layer.blockSignals(True)
        self.combo_layer.clear()

        if not layers:
            self.combo_layer.addItem("(로드된 QGIS 레이어 없음)")
            self.combo_layer.setEnabled(False)
            self.combo_field.clear()
            self.combo_field.setEnabled(False)
            self.combo_layer.blockSignals(False)
            return

        self.combo_layer.setEnabled(True)
        target_idx = -1
        for idx, lyr in enumerate(layers):
            lyr_name = lyr.name() if hasattr(lyr, "name") else str(lyr)
            self.combo_layer.addItem(lyr_name, userData=lyr)
            if lyr_name == saved_layer:
                target_idx = idx

        if target_idx >= 0:
            self.combo_layer.setCurrentIndex(target_idx)
        else:
            # sub, basin, watershed 키워드가 포함된 레이어 우선 선택
            sub_idx = -1
            for i in range(self.combo_layer.count()):
                t = self.combo_layer.itemText(i).lower()
                if any(k in t for k in ["sub", "basin", "watershed"]):
                    sub_idx = i
                    break
            if sub_idx >= 0:
                self.combo_layer.setCurrentIndex(sub_idx)
            else:
                self.combo_layer.setCurrentIndex(0)

        self.combo_layer.blockSignals(False)
        self._on_layer_changed(self.combo_layer.currentText())

    @pyqtSlot(str)
    def _on_layer_changed(self, layer_name: str):
        """선택된 레이어가 변경되었을 때 해당 레이어의 필드 목록을 콤보박스에 채움"""
        if not layer_name or layer_name.startswith("("):
            self.combo_field.clear()
            self.combo_field.setEnabled(False)
            return

        settings.set_selected_layer_name(layer_name)

        layer = self.combo_layer.currentData()
        if not layer or not hasattr(layer, "isValid") or not layer.isValid():
            layer = get_layer_by_name_or_id(layer_name)

        fields = get_layer_fields(layer)
        self.combo_field.blockSignals(True)
        self.combo_field.clear()

        if not fields:
            self.combo_field.setEnabled(False)
            self.combo_field.blockSignals(False)
            return

        self.combo_field.setEnabled(True)
        for fld in fields:
            self.combo_field.addItem(fld)

        saved_field = settings.get_selected_reach_field()
        idx_f = self.combo_field.findText(saved_field)
        if idx_f >= 0:
            self.combo_field.setCurrentIndex(idx_f)
        else:
            rec = detect_reach_id_field(fields)
            if rec:
                rec_idx = self.combo_field.findText(rec)
                if rec_idx >= 0:
                    self.combo_field.setCurrentIndex(rec_idx)
                else:
                    self.combo_field.setCurrentIndex(0)
            else:
                self.combo_field.setCurrentIndex(0)

        self.combo_field.blockSignals(False)
        self._on_field_changed(self.combo_field.currentText())

    @pyqtSlot(str)
    def _on_field_changed(self, field_name: str):
        """선택된 필드가 변경되었을 때 설정 저장 및 맵 툴 대상 필드 갱신"""
        if not field_name:
            return
        settings.set_selected_reach_field(field_name)

        if self.map_tool and hasattr(self.map_tool, "set_reach_field"):
            self.map_tool.set_reach_field(field_name)

    @pyqtSlot()
    def _activate_map_select_tool(self):
        """QGIS 지도 캔버스에서 마우스 클릭으로 소유역을 선택하는 맵 툴 활성화"""
        if not self.iface:
            QMessageBox.information(
                self, "안내", "QGIS 지도 인터페이스가 연동되지 않은 환경입니다."
            )
            return

        try:
            canvas = self.iface.mapCanvas()
            layer_name = self.combo_layer.currentText()
            layer = self.combo_layer.currentData() or get_layer_by_name_or_id(
                layer_name
            )
            reach_field = (
                self.combo_field.currentText() or settings.get_selected_reach_field()
            )

            self.map_tool = SubbasinSelectMapTool(
                canvas,
                iface=self.iface,
                target_layer=layer,
                reach_field=reach_field,
            )
            self.map_tool.reach_selected.connect(self.set_target_reach)
            canvas.setMapTool(self.map_tool)

            if hasattr(self.iface, "messageBar"):
                msg = (
                    "지도에서 분석할 소유역(폴리곤 또는 하천선)을 마우스로 클릭하세요."
                )
                if layer_name and not layer_name.startswith("("):
                    msg += f" [대상 레이어: {layer_name}, 필드: {reach_field}]"
                self.iface.messageBar().pushInfo("SWAT-K", msg)
        except Exception as e:
            QMessageBox.warning(self, "오류", f"지도 선택 툴 활성화 실패: {str(e)}")

    @pyqtSlot(int)
    def set_target_reach(self, reach_id: int):
        """외부(지도 클릭 등)에서 소유역 번호가 결정되었을 때 호출되는 슬롯"""
        target_item = f"{reach_id}번 소유역"
        idx = self.combo_reach.findText(target_item)
        if idx >= 0:
            self.combo_reach.setCurrentIndex(idx)
        else:
            self.combo_reach.blockSignals(True)
            self.combo_reach.addItem(target_item)
            self.combo_reach.setCurrentText(target_item)
            self.combo_reach.blockSignals(False)

        settings.set_target_reach(reach_id)
        target_layer = self.combo_layer.currentData() or get_layer_by_name_or_id(
            self.combo_layer.currentText()
        )
        reach_field = (
            self.combo_field.currentText() or settings.get_selected_reach_field()
        )
        highlight_subbasin_feature(
            reach_id,
            iface=self.iface,
            target_layer=target_layer,
            reach_field=reach_field,
        )
        self._render_data(silent_error=True)

    @pyqtSlot(str)
    def _on_reach_combo_changed(self, reach_text: str):
        """콤보박스에서 소유역 선택 변경 시"""
        m = re.search(r"(\d+)", reach_text)
        if m:
            reach_id = int(m.group(1))
            settings.set_target_reach(reach_id)
            target_layer = self.combo_layer.currentData() or get_layer_by_name_or_id(
                self.combo_layer.currentText()
            )
            reach_field = (
                self.combo_field.currentText() or settings.get_selected_reach_field()
            )
            highlight_subbasin_feature(
                reach_id,
                iface=self.iface,
                target_layer=target_layer,
                reach_field=reach_field,
            )
            self._render_data(silent_error=True)

    @pyqtSlot(str)
    def _on_year_changed(self, year_text: str):
        """콤보박스에서 대상 연도 선택 변경 시"""
        if year_text and year_text.isdigit():
            settings.set_target_year(year_text)
            self._render_data(silent_error=True)

    @pyqtSlot()
    def _populate_controls_from_data_dir(self):
        """지정된 데이터 폴더에서 소유역 및 연도 목록을 찾아 콤보박스에 채움"""
        dir_path_str = self.lineEdit_data_dir.text().strip() or settings.get_data_dir()
        if not dir_path_str or not Path(dir_path_str).is_dir():
            self._set_empty_state("데이터 폴더 미설정")
            return

        data_dir = Path(dir_path_str)
        rch_path = settings.get_rch_path()

        # 1. 소유역(Reach) 목록 구성
        reaches = find_available_reaches(data_dir, rch_path)
        saved_reach = settings.get_target_reach()

        self.combo_reach.blockSignals(True)
        self.combo_reach.clear()
        for r in reaches:
            self.combo_reach.addItem(f"{r}번 소유역")
        self.combo_reach.setEnabled(True)

        target_reach_str = f"{saved_reach}번 소유역"
        idx_r = self.combo_reach.findText(target_reach_str)
        if idx_r >= 0:
            self.combo_reach.setCurrentIndex(idx_r)
        elif reaches:
            self.combo_reach.setCurrentIndex(0)
            settings.set_target_reach(reaches[0])
        self.combo_reach.blockSignals(False)

        current_reach = self._get_current_reach_id()

        # 2. FlowDuration CSV에서 연도 목록 추출 (현재 reach 기준)
        fd_file = find_flow_duration_file(data_dir, rch_path, reach_id=current_reach)
        if not fd_file:
            fd_file = find_flow_duration_file(data_dir, rch_path, reach_id=1)

        if not fd_file:
            self._set_empty_state("FlowDuration 파일 없음")
            return

        years = extract_years_from_flow_duration(fd_file)
        if not years:
            self._set_empty_state("연도 데이터 없음")
            return

        saved_year = settings.get_target_year()
        self.combo_year.blockSignals(True)
        self.combo_year.clear()
        for y in years:
            self.combo_year.addItem(y)
        self.combo_year.setEnabled(True)

        if saved_year in years:
            self.combo_year.setCurrentText(saved_year)
        else:
            self.combo_year.setCurrentIndex(0)
            settings.set_target_year(years[0])
        self.combo_year.blockSignals(False)

        # 차트 렌더링
        self._render_data(silent_error=True)

    def _set_empty_state(self, message: str):
        self.combo_year.blockSignals(True)
        self.combo_year.clear()
        self.combo_year.addItem(message)
        self.combo_year.setEnabled(False)
        self.combo_year.blockSignals(False)

        self.combo_reach.blockSignals(True)
        self.combo_reach.clear()
        self.combo_reach.addItem(message)
        self.combo_reach.setEnabled(False)
        self.combo_reach.blockSignals(False)

        self.label_banner.setText(f"현재 조회 대상: [ {message} ]")
        self.label_equation.setText("사용자 식: -")
        self.label_equation.setToolTip("수식 정보 없음")
        self.ax_daily.clear()
        self._format_daily_axes()
        self.canvas_daily.draw()
        self.ax_duration.clear()
        self._format_duration_axes()
        self.canvas_duration.draw()
        self.label_max_flow_val.setText("-")
        self.label_peak_flow_val.setText("-")

    @pyqtSlot()
    def _render_data(self, silent_error=False):
        """선택된 소유역, 연도 및 데이터 폴더를 기반으로 차트 및 통계 결과를 갱신"""
        dir_path_str = self.lineEdit_data_dir.text().strip() or settings.get_data_dir()
        if not dir_path_str or not Path(dir_path_str).is_dir():
            if not silent_error:
                QMessageBox.warning(
                    self,
                    "폴더 확인",
                    "유효한 Swat-K 전용 데이터 폴더가 지정되지 않았습니다.",
                )
            return

        data_dir = resolve_effective_data_dir(Path(dir_path_str))
        reach_id = self._get_current_reach_id()
        year_str = self.combo_year.currentText().strip()
        if not year_str.isdigit():
            if not silent_error:
                QMessageBox.warning(
                    self, "연도 선택", "유효한 대상 연도를 선택해주세요."
                )
            return

        year_int = int(year_str)
        rch_path = settings.get_rch_path()

        # 명시적 배너 텍스트 갱신
        banner_text = (
            f"현재 조회 대상: [{reach_id}번 소유역 (Reach {reach_id}) | {year_int}년]"
        )
        self.label_banner.setText(banner_text)

        # 사용자 식(Max_step3_equation.csv) 로드 및 갱신
        eq_file = find_equation_file(data_dir, rch_path)
        equation = read_user_equation(eq_file) if eq_file else ""
        if not equation:
            saved_formula = settings.get_custom_formula()
            if saved_formula:
                equation = saved_formula

        if equation:
            self.label_equation.setText(f"사용자 식: {equation}")
            file_desc = f" ({eq_file.name})" if eq_file else " (설정값)"
            self.label_equation.setToolTip(f"첨두홍수량 계산 수식{file_desc}:\n{equation}")
        else:
            self.label_equation.setText("사용자 식: -")
            self.label_equation.setToolTip("수식 정보 파일(Max_step3_equation.csv)을 찾을 수 없습니다.")

        try:
            # 1. 일단위 유량 데이터 로드
            daily_file = find_daily_flow_file(data_dir, rch_path, reach_id=reach_id)
            flows: list[float] = []
            reach_col_str = str(reach_id)

            if daily_file and daily_file.is_file():
                if daily_file.name == "all.csv" or daily_file.name.endswith("_all.csv"):
                    df_all = pd.read_csv(daily_file, index_col=0)
                    df_all.index = pd.to_datetime(df_all.index, errors="coerce")
                    df_filtered = df_all[df_all.index.year == year_int]
                    target_col = (
                        reach_col_str
                        if reach_col_str in df_filtered.columns
                        else df_filtered.columns[0]
                    )
                    flows = (
                        pd.to_numeric(df_filtered[target_col], errors="coerce")
                        .dropna()
                        .astype(float)
                        .tolist()
                    )
                else:
                    df_daily = pd.read_csv(
                        daily_file, header=None, names=["date", "flow"]
                    )
                    df_daily["date"] = pd.to_datetime(df_daily["date"], errors="coerce")
                    df_filtered = df_daily[df_daily["date"].dt.year == year_int]
                    flows = (
                        pd.to_numeric(df_filtered["flow"], errors="coerce")
                        .dropna()
                        .astype(float)
                        .tolist()
                    )

            info_label = f"- {reach_id}번 소유역 ({year_int}년)"
            if flows:
                self._draw_daily_flow(flows, info_label, year=year_int)
            else:
                self.ax_daily.clear()
                self._format_daily_axes(f"{info_label} (데이터 없음)", year=year_int)
                self.canvas_daily.draw()

            # 2. 유황곡선 데이터 로드
            fd_file = find_flow_duration_file(data_dir, rch_path, reach_id=reach_id)
            duration_flows: list[float] = []
            if fd_file and fd_file.is_file():
                df_fd = pd.read_csv(fd_file, index_col=0)
                col_name = None
                for c in df_fd.columns:
                    if str(c).strip() == year_str:
                        col_name = c
                        break
                if col_name is not None:
                    duration_flows = (
                        pd.to_numeric(df_fd[col_name], errors="coerce")
                        .dropna()
                        .tolist()
                    )

            if duration_flows:
                self._draw_flow_duration(duration_flows, info_label)
            else:
                self.ax_duration.clear()
                self._format_duration_axes(f"{info_label} (데이터 없음)")
                self.canvas_duration.draw()

            # 3. 통계 결과 계산 및 표시
            max_flow = max(flows) if flows else None
            peak_flow = None

            # Max_step3.csv (첨두홍수량 계산 결과 파일) 탐색
            step3_file = None
            if (data_dir / "Max_step3.csv").is_file():
                step3_file = data_dir / "Max_step3.csv"
            elif rch_path:
                c1 = data_dir / f"{Path(rch_path).name}_Max_step3.csv"
                c2 = data_dir / f"{Path(rch_path).stem}_Max_step3.csv"
                if c1.is_file():
                    step3_file = c1
                elif c2.is_file():
                    step3_file = c2
            if not step3_file:
                m = sorted(data_dir.glob("*Max_step3.csv"))
                if m:
                    step3_file = m[0]

            if step3_file and step3_file.is_file():
                try:
                    df_step3 = pd.read_csv(step3_file, index_col=0)
                    if year_int in df_step3.index:
                        col = (
                            reach_col_str
                            if reach_col_str in df_step3.columns
                            else df_step3.columns[0]
                        )
                        peak_val = float(df_step3.loc[year_int, col])
                        if peak_val > 0:
                            peak_flow = peak_val
                except Exception as e:
                    log_warning(f"첨두홍수량 파일({step3_file.name}) 파싱 실패: {e}")

            if max_flow is not None:
                self.label_max_flow_val.setText(f"{max_flow:,.2f} m³/s")
            else:
                self.label_max_flow_val.setText("-")

            if peak_flow is not None:
                self.label_peak_flow_val.setText(f"{peak_flow:,.2f} m³/s")
            else:
                self.label_peak_flow_val.setText("-")

        except Exception as e:
            log_error(f"데이터 시각화 중 오류 발생: {e}")
            if not silent_error:
                show_error_message(
                    self,
                    "오류 발생",
                    f"데이터를 시각화하는 중 오류가 발생했습니다:\n{str(e)}",
                )

    def _draw_daily_flow(self, flows: list[float], info_label: str, year: int = 2020):
        self.ax_daily.clear()
        self._format_daily_axes(info_label, year=year)

        if flows:
            self.ax_daily.plot(
                range(len(flows)),
                flows,
                color="#2563EB",
                linewidth=1.2,
                label="유량",
            )
            self.ax_daily.set_xlim(0, max(1, len(flows) - 1))
            self.ax_daily.legend(loc="upper right")

        self.canvas_daily.draw()

    def _draw_flow_duration(self, flow_data: list[float], info_label: str):
        self.ax_duration.clear()
        self._format_duration_axes(info_label)

        filtered = [v for v in flow_data if v > 0]
        if filtered:
            days = range(1, len(filtered) + 1)
            self.ax_duration.plot(
                days, filtered, color="#DC2626", linewidth=1.5, label="유황곡선"
            )
            self.ax_duration.set_xlim(1, max(2, len(filtered)))
            self.ax_duration.legend(loc="upper right")

        self.canvas_duration.draw()

    @pyqtSlot()
    def _save_current_charts(self):
        """현재 렌더링된 두 차트를 고해상도 이미지 파일로 저장"""
        save_dir = QFileDialog.getExistingDirectory(self, "차트 저장 디렉토리 선택")
        if not save_dir:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reach_id = self._get_current_reach_id()
        year_str = (
            self.combo_year.currentText().strip()
            or settings.get_target_year()
            or "chart"
        )
        p_daily = (
            Path(save_dir) / f"daily_flow_reach{reach_id}_{year_str}_{timestamp}.png"
        )
        p_duration = (
            Path(save_dir) / f"flow_duration_reach{reach_id}_{year_str}_{timestamp}.png"
        )

        try:
            self.fig_daily.savefig(str(p_daily), dpi=300, bbox_inches="tight")
            self.fig_duration.savefig(str(p_duration), dpi=300, bbox_inches="tight")
            QMessageBox.information(
                self,
                "저장 완료",
                f"차트 이미지가 성공적으로 저장되었습니다.\n\n"
                f"• 일단위 유량 차트:\n  {p_daily}\n"
                f"• 유황곡선 차트:\n  {p_duration}",
            )
        except Exception as e:
            show_error_message(
                self,
                "저장 오류",
                f"차트 저장 중 오류가 발생했습니다:\n{str(e)}",
            )
