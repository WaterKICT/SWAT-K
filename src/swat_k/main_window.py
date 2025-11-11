"""메인 애플리케이션 윈도우"""

import io
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from swat_k.ui.output_ui import Ui_Form


class MainWindow(QWidget):
    """SWAT PoC 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # UI 텍스트 변경
        self._customize_ui()

        # Signal 연결
        self._connect_signals()

    def _customize_ui(self):
        """UI 커스터마이징"""
        self.ui.lineEdit_rch.setPlaceholderText("CSV 파일 경로를 입력하세요")

    def _connect_signals(self):
        """시그널-슬롯 연결"""
        self.ui.button_browse_rch.clicked.connect(self._browse_rch_file)
        self.ui.button_browse_cio.clicked.connect(self._browse_cio_file)
        self.ui.button_convert.clicked.connect(self._convert_data)
        self.ui.button_read_result.clicked.connect(self._read_result)

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
            rch_chart_path = self._create_and_display_chart(df_rch_filtered)
            cio_chart_path = self._create_and_display_flow_duration_chart(
                df_cio, start_year_int
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

    def _create_and_display_chart(self, df: pd.DataFrame) -> Path:
        """차트 생성 및 QLabel에 표시

        Args:
            df: 날짜와 유량 데이터를 포함한 DataFrame

        Returns:
            저장된 차트 파일 경로
        """
        # matplotlib 한글 폰트 설정
        plt.rcParams["font.family"] = "Malgun Gothic"  # Windows 기본 한글 폰트
        plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

        # Figure 생성
        fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

        # 꺾은선 그래프 그리기
        # 날짜를 MM-DD 형식으로 변환
        dates_mmdd = df["date"].dt.strftime("%m-%d")
        ax.plot(dates_mmdd, df["flow"], linewidth=1, color="#2E86AB")

        # 그래프 스타일링
        ax.set_xlabel("MM-DD", fontsize=10)
        ax.set_ylabel("유량 (m³/s)", fontsize=10)
        ax.set_title("일단위 유량 차트", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.tick_params(axis="both", labelsize=8)

        # x축 레이블 회전 및 간격 조정
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # 적절한 간격으로 x축 레이블 표시 (너무 많지 않게)
        step = max(1, len(dates_mmdd) // 12)  # 최대 12개 레이블 표시
        ax.set_xticks(range(0, len(dates_mmdd), step))
        ax.set_xticklabels(
            [dates_mmdd.iloc[i] for i in range(0, len(dates_mmdd), step)]
        )

        # 레이아웃 조정
        plt.tight_layout()

        # 차트를 파일로 저장
        output_dir = Path("output/charts")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_file = output_dir / f"daily_flow_{timestamp}.png"
        fig.savefig(chart_file, dpi=100, bbox_inches="tight")

        # Figure를 이미지로 변환 (UI 표시용)
        canvas = FigureCanvasAgg(fig)
        buf = io.BytesIO()
        canvas.print_png(buf)
        buf.seek(0)

        # QPixmap으로 변환하여 QLabel에 표시
        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        self.ui.label_chart_daily_flow.setPixmap(
            pixmap.scaled(
                self.ui.label_chart_daily_flow.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        )

        # 메모리 정리
        plt.close(fig)
        buf.close()

        return chart_file

    def _create_and_display_flow_duration_chart(
        self, df: pd.DataFrame, year: int
    ) -> Path:
        """유황곡선 차트 생성 및 QLabel에 표시

        Args:
            df: 연도별 유량 데이터를 포함한 DataFrame
            year: 표시할 연도

        Returns:
            저장된 차트 파일 경로
        """
        # matplotlib 한글 폰트 설정
        plt.rcParams["font.family"] = "Malgun Gothic"  # Windows 기본 한글 폰트
        plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

        # Figure 생성
        fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

        # 해당 연도 데이터 추출
        if year not in df.columns:
            raise ValueError(f"데이터에 {year}년이 없습니다.")

        flow_data = df[year].dropna()  # NaN 값 제거
        day_values = range(1, len(flow_data) + 1)  # Day (1-365/366)

        # 유황곡선 그리기 (로그 스케일 y축)
        ax.plot(day_values, flow_data, linewidth=2, color="#E63946")
        ax.set_yscale("log")

        # 그래프 스타일링
        ax.set_xlabel("Day", fontsize=10)
        ax.set_ylabel("유량 (m³/s)", fontsize=10)
        ax.set_title(
            f"소유역별 연도별 유황곡선 - {year}년", fontsize=12, fontweight="bold"
        )
        ax.grid(True, alpha=0.3, linestyle="--", which="both")
        ax.tick_params(axis="both", labelsize=8)

        # x축 범위 설정 (1-365/366)
        ax.set_xlim(1, len(flow_data))

        # 레이아웃 조정
        plt.tight_layout()

        # 차트를 파일로 저장
        output_dir = Path("output/charts")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_file = output_dir / f"flow_duration_{year}_{timestamp}.png"
        fig.savefig(chart_file, dpi=100, bbox_inches="tight")

        # Figure를 이미지로 변환 (UI 표시용)
        canvas = FigureCanvasAgg(fig)
        buf = io.BytesIO()
        canvas.print_png(buf)
        buf.seek(0)

        # QPixmap으로 변환하여 QLabel에 표시
        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        self.ui.label_chart_flow_duration.setPixmap(
            pixmap.scaled(
                self.ui.label_chart_flow_duration.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        )

        # 메모리 정리
        plt.close(fig)
        buf.close()

        return chart_file

    @Slot()
    def _read_result(self):
        """결과 읽기 및 차트 표시"""
        # TODO: 실제 결과 읽기 및 차트 생성 로직 구현
        QMessageBox.information(self, "결과 읽기", "결과를 읽고 차트를 생성합니다.")
