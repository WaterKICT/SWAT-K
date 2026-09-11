"""[SWAT-K] View 시각화 대화상자 모듈"""

from datetime import datetime
import os
from pathlib import Path
import re

import matplotlib
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from swat_k.core.gis_visualizer import (
    SubbasinSelectMapTool,
    highlight_subbasin_feature,
    load_reach_flows,
    render_swat_layers_to_qgis,
)
from swat_k.utils import settings

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

    rch_name = Path(rch_path).name if rch_path else ""
    rch_stem = Path(rch_path).stem if rch_path else ""

    candidates = []
    if rch_name:
        candidates.extend(
            [
                data_dir / f"{rch_name}_FlowDuration_{reach_id}.csv",
                data_dir / f"{rch_name}_FlowDuration.csv" if reach_id == 1 else None,
            ]
        )
    if rch_stem:
        candidates.extend(
            [
                data_dir / f"{rch_stem}_FlowDuration_{reach_id}.csv",
                data_dir / f"{rch_stem}_FlowDuration.csv" if reach_id == 1 else None,
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
        patterns.extend(["*_FlowDuration.csv", "*_FlowDuration*.csv", "*FlowDuration*.csv"])

    for pattern in patterns:
        matched = sorted(data_dir.glob(pattern))
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
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
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

    rch_name = Path(rch_path).name if rch_path else ""
    rch_stem = Path(rch_path).stem if rch_path else ""

    candidates = []
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
                data_dir / f"{rch_name}_{reach_id}.csv",
                data_dir / f"{rch_name}.csv" if reach_id == 1 else None,
            ]
        )
    if rch_stem:
        candidates.extend(
            [
                data_dir / f"{rch_stem}_{reach_id}.csv",
                data_dir / f"{rch_stem}.csv" if reach_id == 1 else None,
            ]
        )

    for c in candidates:
        if c and c.is_file():
            return c

    # 와일드카드 패턴 검색 (*_{reach_id}.csv 등, 단 FlowDuration이나 Max 제외)
    matched = sorted(data_dir.glob(f"*_{reach_id}.csv"))
    valid = [
        f
        for f in matched
        if not any(k in f.name for k in ["FlowDuration", "Max_step", "all"])
    ]
    if valid:
        return valid[0]

    # _all.csv 확인 (전체 reach가 통합된 파일)
    all_matched = sorted(data_dir.glob("*_all.csv"))
    if all_matched:
        return all_matched[0]

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

    reaches = set()

    # 1. _all.csv 헤더 확인
    for f in data_dir.glob("*_all.csv"):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                line = fp.readline()
            for token in line.split(","):
                token = token.strip()
                if token.isdigit():
                    reaches.add(int(token))
        except Exception:
            pass

    # 2. _FlowDuration_*.csv 패턴 확인
    for f in data_dir.glob("*_FlowDuration_*.csv"):
        m = re.search(r"_FlowDuration_(\d+)\.csv$", f.name)
        if m:
            reaches.add(int(m.group(1)))

    # 3. 개별 하천 시계열 파일 (*_{id}.csv) 확인
    for f in data_dir.glob("*_*.csv"):
        if any(k in f.name for k in ["FlowDuration", "Max_step", "all"]):
            continue
        m = re.search(r"_(\d+)\.csv$", f.name)
        if m:
            reaches.add(int(m.group(1)))

    return sorted(reaches) if reaches else [1]


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

        # 대상 소유역 선택 (Combo + 지도에서 마우스로 선택 버튼)
        self.combo_reach = QComboBox(self)
        self.combo_reach.setMinimumWidth(140)
        self.combo_reach.currentTextChanged.connect(self._on_reach_combo_changed)

        self.btn_select_on_map = QPushButton("지도에서 마우스로 선택", self)
        self.btn_select_on_map.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #EEF2FF; "
            "color: #4338CA; border: 1px solid #C7D2FE; border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #E0E7FF; }"
        )
        self.btn_select_on_map.setToolTip(
            "QGIS 지도에서 마우스 클릭으로 소유역(폴리곤 또는 하천선)을 직접 선택합니다."
        )
        self.btn_select_on_map.clicked.connect(self._activate_map_select_tool)

        layout_reach = QHBoxLayout()
        layout_reach.addWidget(self.combo_reach)
        layout_reach.addWidget(self.btn_select_on_map)
        layout_reach.addStretch()
        layout_controls.addRow("대상 소유역 선택:", layout_reach)

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

        self.label_banner = QLabel("현재 조회 대상: [ -번 소유역  |  - 년 ]", self.banner_frame)
        self.label_banner.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1E40AF;"
        )
        layout_banner.addWidget(self.label_banner)
        layout_banner.addStretch()

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

        self.btn_show_map = QPushButton("QGIS 지도에 표시", self)
        self.btn_show_map.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #2563EB; "
            "color: white; padding: 5px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_show_map.clicked.connect(self._show_on_qgis_map)

        self.btn_save_charts = QPushButton("차트 이미지 저장", self)
        self.btn_save_charts.clicked.connect(self._save_current_charts)
        self.btn_close = QPushButton("닫기", self)
        self.btn_close.clicked.connect(self.close)

        bottom_layout.addWidget(self.btn_refresh)
        bottom_layout.addWidget(self.btn_show_map)
        bottom_layout.addWidget(self.btn_save_charts)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)
        root_layout.addLayout(bottom_layout)

    def _format_daily_axes(self, info_label=""):
        title = f"일단위 유량 차트 {info_label}".strip()
        self.ax_daily.set_title(title, fontdict={"family": "Malgun Gothic"})
        self.ax_daily.set_xlabel("Day Index", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.set_ylabel("유량 (m³/s)", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.grid(True, linestyle="--", alpha=0.5)

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

    def refresh_from_settings(self):
        """외부(예: Run 창 완료 후 또는 플러그인 메인)에서 설정 변경 시 UI 동기화"""
        current_text = self.lineEdit_data_dir.text().strip()
        saved_dir = settings.get_data_dir()
        if saved_dir and saved_dir != current_text:
            self.lineEdit_data_dir.setText(saved_dir)
        self._populate_controls_from_data_dir()

    def showEvent(self, event):
        """대화상자가 화면에 표시될 때 최신 설정 반영"""
        super().showEvent(event)
        self.refresh_from_settings()

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
    def _activate_map_select_tool(self):
        """QGIS 지도 캔버스에서 마우스 클릭으로 소유역을 선택하는 맵 툴 활성화"""
        if not self.iface:
            QMessageBox.information(
                self, "안내", "QGIS 지도 인터페이스가 연동되지 않은 환경입니다."
            )
            return

        try:
            canvas = self.iface.mapCanvas()
            self.map_tool = SubbasinSelectMapTool(canvas, iface=self.iface)
            self.map_tool.reach_selected.connect(self.set_target_reach)
            canvas.setMapTool(self.map_tool)

            if hasattr(self.iface, "messageBar"):
                self.iface.messageBar().pushInfo(
                    "SWAT-K",
                    "지도에서 분석할 소유역(폴리곤 또는 하천선)을 마우스로 클릭하세요.",
                )
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
        highlight_subbasin_feature(reach_id, iface=self.iface)
        self._render_data(silent_error=True)

    @pyqtSlot(str)
    def _on_reach_combo_changed(self, reach_text: str):
        """콤보박스에서 소유역 선택 변경 시"""
        m = re.search(r"(\d+)", reach_text)
        if m:
            reach_id = int(m.group(1))
            settings.set_target_reach(reach_id)
            highlight_subbasin_feature(reach_id, iface=self.iface)
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

        data_dir = Path(dir_path_str)
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
        self.label_banner.setText(
            f"현재 조회 대상: [ {reach_id}번 소유역 (Reach {reach_id})  |  {year_int}년 ]"
        )

        try:
            # 1. 일단위 유량 데이터 로드
            daily_file = find_daily_flow_file(data_dir, rch_path, reach_id=reach_id)
            flows: list[float] = []
            reach_col_str = str(reach_id)

            if daily_file and daily_file.is_file():
                if daily_file.name.endswith("_all.csv"):
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
                    df_daily["date"] = pd.to_datetime(
                        df_daily["date"], errors="coerce"
                    )
                    df_filtered = df_daily[df_daily["date"].dt.year == year_int]
                    flows = (
                        pd.to_numeric(df_filtered["flow"], errors="coerce")
                        .dropna()
                        .astype(float)
                        .tolist()
                    )

            info_label = f"- {reach_id}번 소유역 ({year_int}년)"
            if flows:
                self._draw_daily_flow(flows, info_label)
            else:
                self.ax_daily.clear()
                self._format_daily_axes(f"{info_label} (데이터 없음)")
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
            max_flow = max(flows) if flows else 0.0
            peak_flow = max_flow

            # Max_step3.csv (첨두홍수량 계산 결과 파일) 탐색
            step3_file = None
            if rch_path:
                c1 = data_dir / f"{Path(rch_path).name}_Max_step3.csv"
                c2 = data_dir / f"{Path(rch_path).stem}_Max_step3.csv"
                if c1.is_file():
                    step3_file = c1
                elif c2.is_file():
                    step3_file = c2
            if not step3_file:
                m = sorted(data_dir.glob("*_Max_step3.csv"))
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
                except Exception:
                    pass

            if flows or duration_flows:
                self.label_max_flow_val.setText(f"{max_flow:,.2f} m³/s")
                self.label_peak_flow_val.setText(f"{peak_flow:,.2f} m³/s")
            else:
                self.label_max_flow_val.setText("-")
                self.label_peak_flow_val.setText("-")

        except Exception as e:
            if not silent_error:
                QMessageBox.critical(
                    self,
                    "오류 발생",
                    f"데이터를 시각화하는 중 오류가 발생했습니다:\n{str(e)}",
                )

    def _draw_daily_flow(self, flows: list[float], info_label: str):
        self.ax_daily.clear()
        self._format_daily_axes(info_label)

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
    def _show_on_qgis_map(self):
        """현재 선택된 연도/유량 데이터를 기반으로 하천망을 QGIS 지도에 시각화"""
        stream_shp = settings.get_stream_shp_path()
        subbasin_shp = settings.get_subbasin_shp_path()
        rch_path = settings.get_rch_path()
        data_dir_str = (
            self.lineEdit_data_dir.text().strip() or settings.get_data_dir()
        )
        reach_id = self._get_current_reach_id()
        year_str = (
            self.combo_year.currentText().strip() or settings.get_target_year()
        )

        if not stream_shp or not Path(stream_shp).is_file():
            QMessageBox.warning(
                self,
                "하천망 Shapefile 미설정",
                "등록된 하천망 Shapefile이 없습니다.\n\n"
                "[SWAT-K] Run 대화상자에서 하천망 Shapefile(.shp)을 먼저 지정해주세요.",
            )
            return

        year_int = int(year_str) if str(year_str).isdigit() else None
        year_label = f" ({year_int}년)" if year_int else ""

        # rch_path 검증 및 data_dir 기준 파일 우선 탐색
        target_rch = rch_path
        if data_dir_str and Path(data_dir_str).is_dir():
            data_dir = Path(data_dir_str)
            if rch_path and (data_dir / Path(rch_path).name).is_file():
                target_rch = str(data_dir / Path(rch_path).name)
            else:
                rch_files = list(data_dir.glob("*.rch"))
                if rch_files:
                    target_rch = str(rch_files[0])
                else:
                    all_files = list(data_dir.glob("*_all.csv"))
                    if all_files:
                        target_rch = str(all_files[0])

        flow_data = load_reach_flows(
            target_rch, year=year_int, aggregate_mode="max"
        )

        success, msg = render_swat_layers_to_qgis(
            stream_shp_path=stream_shp,
            subbasin_shp_path=subbasin_shp,
            flow_data=flow_data,
            year_label=year_label,
            iface=self.iface,
        )

        if success:
            # 선택된 소유역 피처 하이라이트
            highlight_subbasin_feature(reach_id, iface=self.iface)
            QMessageBox.information(self, "QGIS 지도 표출 완료", msg)
        else:
            QMessageBox.warning(self, "QGIS 지도 표출 실패", msg)

    @pyqtSlot()
    def _save_current_charts(self):
        """현재 렌더링된 두 차트를 고해상도 이미지 파일로 저장"""
        save_dir = QFileDialog.getExistingDirectory(
            self, "차트 저장 디렉토리 선택"
        )
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
            Path(save_dir)
            / f"flow_duration_reach{reach_id}_{year_str}_{timestamp}.png"
        )

        try:
            self.fig_daily.savefig(str(p_daily), dpi=300, bbox_inches="tight")
            self.fig_duration.savefig(
                str(p_duration), dpi=300, bbox_inches="tight"
            )
            QMessageBox.information(
                self,
                "저장 완료",
                f"차트 이미지가 성공적으로 저장되었습니다.\n\n"
                f"• 일단위 유량 차트:\n  {p_daily}\n"
                f"• 유황곡선 차트:\n  {p_duration}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "저장 오류",
                f"차트 저장 중 오류가 발생했습니다:\n{str(e)}",
            )
