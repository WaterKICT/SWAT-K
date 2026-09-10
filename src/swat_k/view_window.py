"""[SWAT-K] View 시각화 대화상자 모듈"""

from datetime import datetime
from pathlib import Path

import matplotlib
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from swat_k.utils import settings

try:
    from qgis.PyQt.QtCore import pyqtSlot
    from qgis.PyQt.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide6.QtCore import Slot as pyqtSlot
    from PySide6.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False


class ViewDialog(QDialog):
    """SWAT 데이터 차트 시각화 및 결과 조회 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("[SWAT-K] View - 데이터 시각화")
        self.resize(880, 820)
        self.setMinimumSize(640, 500)

        self._init_ui()
        self._load_saved_settings()

        # 설정된 파일이 존재할 경우 초기 자동 렌더링 시도
        self._auto_load_if_ready()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. 스크롤 영역 (차트 2개 및 통계 결과)
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

        # 2. 하단 액션 버튼
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

    def _format_daily_axes(self, year_label=""):
        self.ax_daily.set_title(
            f"일단위 유량 차트 {year_label}".strip(),
            fontdict={"family": "Malgun Gothic"},
        )
        self.ax_daily.set_xlabel("Day Index", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.set_ylabel("유량 (m³/s)", fontdict={"family": "Malgun Gothic"})
        self.ax_daily.grid(True, linestyle="--", alpha=0.5)

    def _format_duration_axes(self, year_label=""):
        self.ax_duration.set_title(
            f"소유역별 연도별 유황곡선 {year_label}".strip(),
            fontdict={"family": "Malgun Gothic"},
        )
        self.ax_duration.set_xlabel("Day", fontdict={"family": "Malgun Gothic"})
        self.ax_duration.set_ylabel("유량 (m³/s)", fontdict={"family": "Malgun Gothic"})
        self.ax_duration.set_yscale("log")
        self.ax_duration.grid(True, which="both", linestyle="--", alpha=0.5)

    def _load_saved_settings(self):
        """저장된 설정 불러오기"""
        pass

    def _auto_load_if_ready(self):
        """기존 설정 파일이 유효하면 자동으로 차트 렌더링"""
        rch_path = settings.get_rch_path()
        cio_path = settings.get_cio_path()
        year_str = settings.get_start_year()

        if (
            rch_path
            and Path(rch_path).is_file()
            and cio_path
            and Path(cio_path).is_file()
            and year_str.isdigit()
        ):
            self._render_data(silent_error=True)

    @pyqtSlot()
    def _render_data(self, silent_error=False):
        """데이터를 불러와 차트 및 통계 결과를 갱신"""
        rch_file = settings.get_rch_path()
        cio_file = settings.get_cio_path()
        year_str = settings.get_start_year()

        if not rch_file or not Path(rch_file).is_file():
            if not silent_error:
                QMessageBox.warning(
                    self, "설정 확인", "설정된 RCH 파일이 존재하지 않습니다."
                )
            return

        if not cio_file or not Path(cio_file).is_file():
            if not silent_error:
                QMessageBox.warning(
                    self, "설정 확인", "설정된 CIO 파일이 존재하지 않습니다."
                )
            return

        if not str(year_str).isdigit():
            if not silent_error:
                QMessageBox.warning(self, "설정 확인", "유효한 시작 연도가 설정되지 않았습니다.")
            return

        year_int = int(year_str)

        try:
            # 1. RCH 데이터 로드 및 필터링
            df_rch = pd.read_csv(rch_file, header=None, names=["date", "flow"])
            df_rch["date"] = pd.to_datetime(df_rch["date"])
            df_rch_filtered = df_rch[df_rch["date"].dt.year == year_int]

            if df_rch_filtered.empty:
                if not silent_error:
                    QMessageBox.warning(
                        self,
                        "데이터 없음",
                        f"RCH 파일에 {year_int}년 데이터가 없습니다.",
                    )
                return

            # 2. CIO 데이터 로드 및 검증
            df_cio = pd.read_csv(cio_file, index_col=0)
            df_cio.columns = [
                int(c) if not str(c).startswith("Unnamed") else c
                for c in df_cio.columns
            ]
            numeric_cols = [c for c in df_cio.columns if isinstance(c, int)]
            df_cio = df_cio[numeric_cols]

            if year_int not in df_cio.columns:
                if not silent_error:
                    QMessageBox.warning(
                        self,
                        "데이터 없음",
                        f"CIO 파일에 {year_int}년 데이터가 없습니다.",
                    )
                return

            # 3. 차트 갱신
            self._draw_daily_flow(df_rch_filtered, year_int)
            self._draw_flow_duration(df_cio, year_int)

            # 4. 통계 결과 계산 및 표시
            flows = df_rch_filtered["flow"].astype(float)
            max_flow = flows.max()
            # 첨두홍수량: 연중 최대 유량 값
            peak_flow = max_flow

            self.label_max_flow_val.setText(f"{max_flow:,.2f} m³/s")
            self.label_peak_flow_val.setText(f"{peak_flow:,.2f} m³/s")

        except Exception as e:
            if not silent_error:
                QMessageBox.critical(
                    self,
                    "오류 발생",
                    f"데이터를 시각화하는 중 오류가 발생했습니다:\n{str(e)}",
                )

    def _draw_daily_flow(self, df: pd.DataFrame, year: int):
        self.ax_daily.clear()
        self._format_daily_axes(f"- {year}년")

        flows = df["flow"].astype(float).tolist()
        if flows:
            self.ax_daily.plot(
                range(len(flows)), flows, color="#2563EB", linewidth=1.2, label="유량"
            )
            self.ax_daily.set_xlim(0, max(0, len(flows) - 1))
            self.ax_daily.legend(loc="upper right")

        self.canvas_daily.draw()

    def _draw_flow_duration(self, df: pd.DataFrame, year: int):
        self.ax_duration.clear()
        self._format_duration_axes(f"- {year}년")

        flow_data = df[year].dropna().astype(float).tolist()
        filtered = [v for v in flow_data if v > 0]
        if filtered:
            days = range(1, len(filtered) + 1)
            self.ax_duration.plot(
                days, filtered, color="#DC2626", linewidth=1.5, label="유황곡선"
            )
            self.ax_duration.set_xlim(1, max(1, len(filtered)))
            self.ax_duration.legend(loc="upper right")

        self.canvas_duration.draw()

    @pyqtSlot()
    def _save_current_charts(self):
        """현재 렌더링된 두 차트를 고해상도 이미지 파일로 저장"""
        save_dir = QFileDialog.getExistingDirectory(self, "차트 저장 디렉토리 선택")
        if not save_dir:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        year_str = settings.get_start_year() or "chart"
        p_daily = Path(save_dir) / f"daily_flow_{year_str}_{timestamp}.png"
        p_duration = Path(save_dir) / f"flow_duration_{year_str}_{timestamp}.png"

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
            QMessageBox.critical(
                self, "저장 오류", f"차트 저장 중 오류가 발생했습니다:\n{str(e)}"
            )
