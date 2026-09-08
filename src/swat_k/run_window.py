"""[SWAT-K] Run 대화상자 모듈"""

from pathlib import Path

try:
    from qgis.PyQt.QtCore import Qt, pyqtSlot
    from qgis.PyQt.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )
except ImportError:
    from PySide6.QtCore import Qt
    from PySide6.QtCore import Slot as pyqtSlot
    from PySide6.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

from swat_k.utils import settings


class RunDialog(QDialog):
    """SWAT-K Converter 실행 설정 및 입력 파일 지정 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("[SWAT-K] Run - Converter 실행")
        self.resize(600, 320)
        self._init_ui()
        self._load_saved_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. 설정 그룹박스
        group_box = QGroupBox("SWAT-K Converter 및 입력 파일 지정", self)
        form_layout = QFormLayout(group_box)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(10)

        # SWAT-K Converter 프로그램 지정 (.exe)
        self.lineEdit_exe = QLineEdit(self)
        self.lineEdit_exe.setPlaceholderText("SWAT-K Converter (.exe) 경로 선택")
        self.btn_browse_exe = QPushButton("찾아보기...", self)
        self.btn_browse_exe.clicked.connect(self._browse_exe_file)

        layout_exe = QHBoxLayout()
        layout_exe.addWidget(self.lineEdit_exe)
        layout_exe.addWidget(self.btn_browse_exe)
        form_layout.addRow("Converter 프로그램 (.exe):", layout_exe)

        # RCH 파일 지정
        self.lineEdit_rch = QLineEdit(self)
        self.lineEdit_rch.setPlaceholderText("RCH 또는 CSV 파일 경로를 선택하세요")
        self.btn_browse_rch = QPushButton("찾아보기...", self)
        self.btn_browse_rch.clicked.connect(self._browse_rch_file)

        layout_rch = QHBoxLayout()
        layout_rch.addWidget(self.lineEdit_rch)
        layout_rch.addWidget(self.btn_browse_rch)
        form_layout.addRow("RCH file 지정:", layout_rch)

        # CIO 파일 지정
        self.lineEdit_cio = QLineEdit(self)
        self.lineEdit_cio.setPlaceholderText("CIO 또는 CSV 파일 경로를 선택하세요")
        self.btn_browse_cio = QPushButton("찾아보기...", self)
        self.btn_browse_cio.clicked.connect(self._browse_cio_file)

        layout_cio = QHBoxLayout()
        layout_cio.addWidget(self.lineEdit_cio)
        layout_cio.addWidget(self.btn_browse_cio)
        form_layout.addRow("CIO file 지정:", layout_cio)

        # 시작 연도 (start year)
        self.lineEdit_year = QLineEdit(self)
        self.lineEdit_year.setPlaceholderText("예: 1980")
        form_layout.addRow("시작 연도 (start year):", self.lineEdit_year)

        main_layout.addWidget(group_box)

        # 2. 하단 실행 및 닫기 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_run = QPushButton("Converter 실행", self)
        self.btn_run.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 6px 18px; }"
        )
        self.btn_run.clicked.connect(self._on_run_clicked)

        self.btn_close = QPushButton("닫기", self)
        self.btn_close.clicked.connect(self.close)

        button_layout.addWidget(self.btn_run)
        button_layout.addWidget(self.btn_close)
        main_layout.addLayout(button_layout)

    def _load_saved_settings(self):
        """이전에 저장된 경로 및 설정값 불러오기"""
        saved_exe = settings.get_converter_exe_path()
        saved_rch = settings.get_rch_path()
        saved_cio = settings.get_cio_path()
        saved_year = settings.get_start_year()

        if saved_exe:
            self.lineEdit_exe.setText(saved_exe)
        if saved_rch:
            self.lineEdit_rch.setText(saved_rch)
        if saved_cio:
            self.lineEdit_cio.setText(saved_cio)
        if saved_year:
            self.lineEdit_year.setText(saved_year)

    def _save_current_settings(self):
        """현재 입력된 경로 및 설정값 저장"""
        settings.set_converter_exe_path(self.lineEdit_exe.text().strip())
        settings.set_rch_path(self.lineEdit_rch.text().strip())
        settings.set_cio_path(self.lineEdit_cio.text().strip())
        settings.set_start_year(self.lineEdit_year.text().strip())

    @pyqtSlot()
    def _browse_exe_file(self):
        """Converter .exe 파일 선택"""
        current_dir = ""
        if self.lineEdit_exe.text():
            p = Path(self.lineEdit_exe.text())
            if p.parent.exists():
                current_dir = str(p.parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "SWAT-K Converter 프로그램 선택",
            current_dir,
            "실행 파일 (*.exe);;모든 파일 (*)",
        )
        if file_path:
            self.lineEdit_exe.setText(file_path)
            settings.set_converter_exe_path(file_path)

    @pyqtSlot()
    def _browse_rch_file(self):
        """RCH 파일 선택"""
        current_dir = ""
        if self.lineEdit_rch.text():
            p = Path(self.lineEdit_rch.text())
            if p.parent.exists():
                current_dir = str(p.parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "RCH 파일 선택",
            current_dir,
            "RCH 및 CSV 파일 (*.rch *.csv);;모든 파일 (*)",
        )
        if file_path:
            self.lineEdit_rch.setText(file_path)
            settings.set_rch_path(file_path)

    @pyqtSlot()
    def _browse_cio_file(self):
        """CIO 파일 선택"""
        current_dir = ""
        if self.lineEdit_cio.text():
            p = Path(self.lineEdit_cio.text())
            if p.parent.exists():
                current_dir = str(p.parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "CIO 파일 선택",
            current_dir,
            "CIO 및 CSV 파일 (*.cio *.csv);;모든 파일 (*)",
        )
        if file_path:
            self.lineEdit_cio.setText(file_path)
            settings.set_cio_path(file_path)

    @pyqtSlot()
    def _on_run_clicked(self):
        """Converter 실행 버튼 클릭 이벤트"""
        exe_path = self.lineEdit_exe.text().strip()
        rch_path = self.lineEdit_rch.text().strip()
        cio_path = self.lineEdit_cio.text().strip()
        start_year = self.lineEdit_year.text().strip()

        if not exe_path:
            QMessageBox.warning(
                self, "입력 오류", "SWAT-K Converter 프로그램(.exe)을 지정해주세요."
            )
            return

        if not rch_path:
            QMessageBox.warning(self, "입력 오류", "RCH 파일을 지정해주세요.")
            return

        if not cio_path:
            QMessageBox.warning(self, "입력 오류", "CIO 파일을 지정해주세요.")
            return

        if start_year and not start_year.isdigit():
            QMessageBox.warning(self, "입력 오류", "시작 연도는 숫자여야 합니다.")
            return

        # 설정값 영속화
        self._save_current_settings()

        # 사용자 요청 사항: 아직 실행 인자 규격이 미정이므로 안내 메시지 출력
        info_msg = (
            "SWAT-K Converter 연동 기능은 현재 개발 중입니다.\n\n"
            f"• 지정된 실행 파일:\n  {exe_path}\n"
            f"• RCH 파일:\n  {rch_path}\n"
            f"• CIO 파일:\n  {cio_path}\n"
            f"• 시작 연도: {start_year if start_year else '미지정'}"
        )
        QMessageBox.information(self, "안내", info_msg)
