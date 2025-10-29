"""메인 애플리케이션 윈도우"""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from swat_k.ui.output_ui import Ui_Form


class MainWindow(QWidget):
    """SWAT PoC 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Signal 연결
        self._connect_signals()

    def _connect_signals(self):
        """시그널-슬롯 연결"""
        self.ui.button_browse_rch.clicked.connect(self._browse_rch_file)
        self.ui.button_browse_cio.clicked.connect(self._browse_cio_file)
        self.ui.button_convert.clicked.connect(self._convert_data)
        self.ui.button_read_result.clicked.connect(self._read_result)

    @Slot()
    def _browse_rch_file(self):
        """RCH 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "RCH 파일 선택", "", "RCH Files (*.rch);;All Files (*)"
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
        cio_file = self.ui.lineEdit_cio.text()
        start_year = self.ui.lineEdit_year.text()

        # 입력 검증
        if not rch_file or not cio_file:
            QMessageBox.warning(
                self, "입력 오류", "RCH 파일과 CIO 파일을 모두 지정해주세요."
            )
            return

        if not start_year.isdigit():
            QMessageBox.warning(self, "입력 오류", "시작 연도는 숫자여야 합니다.")
            return

        # TODO: 실제 변환 로직 구현
        QMessageBox.information(
            self,
            "변환 시작",
            f"데이터 변환을 시작합니다.\n"
            f"RCH: {rch_file}\n"
            f"CIO: {cio_file}\n"
            f"Start Year: {start_year}",
        )

    @Slot()
    def _read_result(self):
        """결과 읽기 및 차트 표시"""
        # TODO: 실제 결과 읽기 및 차트 생성 로직 구현
        QMessageBox.information(self, "결과 읽기", "결과를 읽고 차트를 생성합니다.")
