"""메인 애플리케이션 윈도우"""

import io

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
            self, "CIO 파일 선택", "", "CIO Files (*.cio);;All Files (*)"
        )
        if file_path:
            self.ui.lineEdit_cio.setText(file_path)

    @Slot()
    def _convert_data(self):
        """데이터 변환 실행"""
        rch_file = self.ui.lineEdit_rch.text()
        start_year = self.ui.lineEdit_year.text()

        # 입력 검증
        if not rch_file:
            QMessageBox.warning(self, "입력 오류", "RCH 파일을 지정해주세요.")
            return

        if not start_year.isdigit():
            QMessageBox.warning(self, "입력 오류", "시작 연도는 숫자여야 합니다.")
            return

        try:
            # CSV 파일 읽기
            df = self._load_rch_file(rch_file)

            # 시작 연도로 필터링
            start_year_int = int(start_year)
            df_filtered = df[df["date"].dt.year >= start_year_int]

            if df_filtered.empty:
                QMessageBox.warning(
                    self, "데이터 없음", f"{start_year}년 이후 데이터가 없습니다."
                )
                return

            # 차트 생성 및 표시
            self._create_and_display_chart(df_filtered)

            QMessageBox.information(
                self,
                "변환 완료",
                f"데이터 변환이 완료되었습니다.\n"
                f"총 {len(df_filtered)}개의 데이터 포인트가 표시됩니다.",
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

    def _create_and_display_chart(self, df: pd.DataFrame):
        """차트 생성 및 QLabel에 표시

        Args:
            df: 날짜와 유량 데이터를 포함한 DataFrame
        """
        # matplotlib 한글 폰트 설정
        plt.rcParams["font.family"] = "Malgun Gothic"  # Windows 기본 한글 폰트
        plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

        # Figure 생성
        fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

        # 꺾은선 그래프 그리기
        ax.plot(df["date"], df["flow"], linewidth=1, color="#2E86AB")

        # 그래프 스타일링
        ax.set_xlabel("날짜", fontsize=10)
        ax.set_ylabel("유량 (m³/s)", fontsize=10)
        ax.set_title("일단위 유량 차트", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.tick_params(axis="both", labelsize=8)

        # x축 날짜 포맷 설정
        fig.autofmt_xdate()

        # 레이아웃 조정
        plt.tight_layout()

        # Figure를 이미지로 변환
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

    @Slot()
    def _read_result(self):
        """결과 읽기 및 차트 표시"""
        # TODO: 실제 결과 읽기 및 차트 생성 로직 구현
        QMessageBox.information(self, "결과 읽기", "결과를 읽고 차트를 생성합니다.")
