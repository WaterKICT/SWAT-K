"""메인 애플리케이션 윈도우"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QMargins, Qt, Slot
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QLogValueAxis, QValueAxis
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox, QSizePolicy, QWidget

from swat_k.ui.output_ui import Ui_Form


class MainWindow(QWidget):
    """SWAT PoC 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self._init_charts()

        self._configure_layout_stretch()

        # UI 텍스트 변경
        self._customize_ui()

        # Signal 연결
        self._connect_signals()

    def _customize_ui(self):
        """UI 커스터마이징"""
        self.ui.lineEdit_rch.setPlaceholderText("CSV 파일 경로를 입력하세요")

    def _configure_layout_stretch(self) -> None:
        self.ui.groupBox_Output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Main layout: let Output expand; avoid bottom spacer consuming all extra height
        self.ui.verticalLayout_Main.setStretch(0, 0)
        self.ui.verticalLayout_Main.setStretch(1, 1)
        self.ui.verticalLayout_Main.setStretch(2, 0)

    def _init_charts(self):
        self.ui.label_chart_daily_flow.hide()
        self.ui.label_chart_flow_duration.hide()

        chart_min_h = max(
            200,
            int(self.ui.label_chart_daily_flow.minimumSize().height() or 0),
            int(self.ui.label_chart_flow_duration.minimumSize().height() or 0),
        )

        self.daily_flow_chart = QChart()
        self.daily_flow_chart.legend().hide()
        self.daily_flow_chart.setTitle("일단위 유량 차트")
        self.daily_flow_chart.setMargins(QMargins(0, 0, 0, 0))
        self.daily_flow_series = QLineSeries()
        self.daily_flow_chart.addSeries(self.daily_flow_series)
        self.daily_flow_axis_x = QValueAxis()
        self.daily_flow_axis_x.setLabelFormat("%d")
        self.daily_flow_axis_x.setTitleText("Day Index")
        self.daily_flow_axis_y = QValueAxis()
        self.daily_flow_axis_y.setTitleText("유량 (m³/s)")
        self.daily_flow_chart.addAxis(self.daily_flow_axis_x, Qt.AlignBottom)
        self.daily_flow_chart.addAxis(self.daily_flow_axis_y, Qt.AlignLeft)
        self.daily_flow_series.attachAxis(self.daily_flow_axis_x)
        self.daily_flow_series.attachAxis(self.daily_flow_axis_y)

        self.daily_flow_chart_view = QChartView(self.daily_flow_chart, self)
        self.daily_flow_chart_view.setRenderHint(QPainter.Antialiasing)
        self.daily_flow_chart_view.setMinimumHeight(chart_min_h)
        self.daily_flow_chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.flow_duration_chart = QChart()
        self.flow_duration_chart.legend().hide()
        self.flow_duration_chart.setTitle("소유역별 연도별 유황곡선")
        self.flow_duration_chart.setMargins(QMargins(0, 0, 0, 0))
        self.flow_duration_series = QLineSeries()
        self.flow_duration_chart.addSeries(self.flow_duration_series)
        self.flow_duration_axis_x = QValueAxis()
        self.flow_duration_axis_x.setLabelFormat("%d")
        self.flow_duration_axis_x.setTitleText("Day")
        self.flow_duration_axis_y = QLogValueAxis()
        self.flow_duration_axis_y.setBase(10)
        self.flow_duration_axis_y.setLabelFormat("%.0f")
        self.flow_duration_axis_y.setTitleText("유량 (m³/s)")
        self.flow_duration_chart.addAxis(self.flow_duration_axis_x, Qt.AlignBottom)
        self.flow_duration_chart.addAxis(self.flow_duration_axis_y, Qt.AlignLeft)
        self.flow_duration_series.attachAxis(self.flow_duration_axis_x)
        self.flow_duration_series.attachAxis(self.flow_duration_axis_y)

        self.flow_duration_chart_view = QChartView(self.flow_duration_chart, self)
        self.flow_duration_chart_view.setRenderHint(QPainter.Antialiasing)
        self.flow_duration_chart_view.setMinimumHeight(chart_min_h)
        self.flow_duration_chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        daily_idx = self.ui.verticalLayout_Output.indexOf(self.ui.label_chart_daily_flow)
        self.ui.verticalLayout_Output.insertWidget(daily_idx + 1, self.daily_flow_chart_view)
        flow_idx = self.ui.verticalLayout_Output.indexOf(self.ui.label_chart_flow_duration)
        self.ui.verticalLayout_Output.insertWidget(flow_idx + 1, self.flow_duration_chart_view)

        # Let charts consume available vertical space inside Output
        self.ui.verticalLayout_Output.setStretch(self.ui.verticalLayout_Output.indexOf(self.daily_flow_chart_view), 1)
        self.ui.verticalLayout_Output.setStretch(self.ui.verticalLayout_Output.indexOf(self.flow_duration_chart_view), 1)

    def _connect_signals(self):
        """시그널-슬롯 연결"""
        self.ui.button_browse_rch.clicked.connect(self._browse_rch_file)
        self.ui.button_browse_cio.clicked.connect(self._browse_cio_file)
        self.ui.button_convert.clicked.connect(self._convert_data)
        self.ui.button_read_result.clicked.connect(self._read_result)

    def _save_chart_snapshot(self, chart_view: QChartView, output_path: Path) -> Path:
        pixmap = chart_view.grab()
        if not pixmap.save(str(output_path), "PNG"):
            raise RuntimeError(f"차트 저장에 실패했습니다: {output_path}")
        return output_path

    @Slot()
    def _browse_rch_file(self):
        """CSV 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 선택", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.ui.lineEdit_rch.setText(file_path)

    @Slot()
    def _browse_cio_file(self):
        """CIO 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CIO 파일 선택", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.ui.lineEdit_cio.setText(file_path)

    @Slot()
    def _convert_data(self):
        """데이터 변환 실행"""
        rch_file = self.ui.lineEdit_rch.text()
        cio_file = self.ui.lineEdit_cio.text()
        start_year = self.ui.lineEdit_year.text()

        # 입력 검증
        if not rch_file:
            QMessageBox.warning(self, "입력 오류", "RCH 파일을 지정해주세요.")
            return

        if not cio_file:
            QMessageBox.warning(self, "입력 오류", "CIO 파일을 지정해주세요.")
            return

        if not start_year.isdigit():
            QMessageBox.warning(self, "입력 오류", "시작 연도는 숫자여야 합니다.")
            return

        try:
            # RCH CSV 파일 읽기
            df_rch = self._load_rch_file(rch_file)

            # 시작 연도로 필터링 (특정 연도만)
            start_year_int = int(start_year)
            df_rch_filtered = df_rch[df_rch["date"].dt.year == start_year_int]

            if df_rch_filtered.empty:
                QMessageBox.warning(
                    self, "데이터 없음", f"{start_year}년 데이터가 없습니다."
                )
                return

            # CIO 파일 읽기 및 처리
            df_cio = self._load_cio_file(cio_file)
            if start_year_int not in df_cio.columns:
                QMessageBox.warning(
                    self, "데이터 없음", f"CIO 파일에 {start_year}년 데이터가 없습니다."
                )
                return

            # 차트 생성 및 표시
            self._update_daily_flow_chart(df_rch_filtered)
            self._update_flow_duration_chart(df_cio, start_year_int)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rch_dir = Path(rch_file).resolve().parent
            cio_dir = Path(cio_file).resolve().parent

            rch_chart_path = self._save_chart_snapshot(
                self.daily_flow_chart_view,
                rch_dir / f"daily_flow_{start_year_int}_{timestamp}.png",
            )
            cio_chart_path = self._save_chart_snapshot(
                self.flow_duration_chart_view,
                cio_dir / f"flow_duration_{start_year_int}_{timestamp}.png",
            )

            QMessageBox.information(
                self,
                "변환 완료",
                f"데이터 변환이 완료되었습니다.\n"
                f"일단위 유량: {len(df_rch_filtered)}개 데이터 포인트\n"
                f"유황곡선: {len(df_cio)}개 데이터 포인트\n\n"
                f"일단위 유량 차트: {rch_chart_path}\n"
                f"유황곡선 차트: {cio_chart_path}",
            )

        except Exception as e:
            QMessageBox.critical(
                self, "오류 발생", f"데이터 처리 중 오류가 발생했습니다:\n{str(e)}"
            )

    def _load_rch_file(self, file_path: str) -> pd.DataFrame:
        """RCH CSV 파일 로드

        Args:
            file_path: CSV 파일 경로

        Returns:
            날짜와 유량 데이터를 포함한 DataFrame
        """
        df = pd.read_csv(file_path, header=None, names=["date", "flow"])
        df["date"] = pd.to_datetime(df["date"])
        return df

    def _load_cio_file(self, file_path: str) -> pd.DataFrame:
        """CIO 유황곡선 파일 로드

        Args:
            file_path: CSV 파일 경로

        Returns:
            연도별 유량 데이터를 포함한 DataFrame
        """
        df = pd.read_csv(file_path, index_col=0)
        # 첫 번째 컬럼(인덱스)을 제외한 나머지 컬럼명을 정수형으로 변환
        # 'Unnamed'로 시작하는 컬럼은 건너뛰기
        df.columns = [
            int(col) if not str(col).startswith('Unnamed') else col
            for col in df.columns
        ]
        # 숫자 컬럼만 필터링
        numeric_cols = [col for col in df.columns if isinstance(col, int)]
        df = df[numeric_cols]
        return df

    def _update_daily_flow_chart(self, df: pd.DataFrame) -> None:
        self.daily_flow_series.clear()

        flows = df["flow"].astype(float).tolist()
        for i, y in enumerate(flows):
            self.daily_flow_series.append(float(i), float(y))

        if flows:
            self.daily_flow_axis_x.setRange(0, max(0, len(flows) - 1))
            min_y = min(flows)
            max_y = max(flows)
            if min_y == max_y:
                max_y = min_y + 1.0
            self.daily_flow_axis_y.setRange(float(min_y), float(max_y))

    def _update_flow_duration_chart(self, df: pd.DataFrame, year: int) -> None:
        if year not in df.columns:
            raise ValueError(f"데이터에 {year}년이 없습니다.")

        self.flow_duration_chart.setTitle(f"소유역별 연도별 유황곡선 - {year}년")
        self.flow_duration_series.clear()

        flow_data = df[year].dropna().astype(float).tolist()

        # 로그축에서는 0 이하 값은 표현 불가하므로 제거
        filtered = [v for v in flow_data if v > 0]
        for day, y in enumerate(filtered, start=1):
            self.flow_duration_series.append(float(day), float(y))

        if filtered:
            self.flow_duration_axis_x.setRange(1, max(1, len(filtered)))
            min_y = min(filtered)
            max_y = max(filtered)
            if min_y == max_y:
                max_y = min_y * 10.0
            self.flow_duration_axis_y.setRange(float(min_y), float(max_y))

    @Slot()
    def _read_result(self):
        """결과 읽기 및 차트 표시"""
        # TODO: 실제 결과 읽기 및 차트 생성 로직 구현
        QMessageBox.information(self, "결과 읽기", "결과를 읽고 차트를 생성합니다.")
