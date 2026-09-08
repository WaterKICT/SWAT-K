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

from swat_k.core.formula import DEFAULT_FORMULA, validate_formula
from swat_k.utils import settings


class RunDialog(QDialog):
    """SWAT-K Converter 실행 설정 및 입력 파일 지정 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("[SWAT-K] Run - Converter 실행")
        self.resize(620, 320)
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

        # RCH 파일 경로 선택
        self.lineEdit_rch = QLineEdit(self)
        self.lineEdit_rch.setPlaceholderText("RCH 파일 경로를 선택하세요")
        self.btn_browse_rch = QPushButton("찾아보기...", self)
        self.btn_browse_rch.clicked.connect(self._browse_rch_file)

        layout_rch = QHBoxLayout()
        layout_rch.addWidget(self.lineEdit_rch)
        layout_rch.addWidget(self.btn_browse_rch)
        form_layout.addRow("RCH 파일 경로:", layout_rch)

        # CIO 파일 경로 선택
        self.lineEdit_cio = QLineEdit(self)
        self.lineEdit_cio.setPlaceholderText("CIO 파일 경로를 선택하세요")
        self.btn_browse_cio = QPushButton("찾아보기...", self)
        self.btn_browse_cio.clicked.connect(self._browse_cio_file)

        layout_cio = QHBoxLayout()
        layout_cio.addWidget(self.lineEdit_cio)
        layout_cio.addWidget(self.btn_browse_cio)
        form_layout.addRow("CIO 파일 경로:", layout_cio)

        # 사용자 정의 식
        self.lineEdit_formula = QLineEdit(self)
        self.lineEdit_formula.setText(DEFAULT_FORMULA)
        self.lineEdit_formula.setPlaceholderText(DEFAULT_FORMULA)
        self.lineEdit_formula.setToolTip(
            "v0, v1, v2 변수가 반드시 포함되어야 하며,\n"
            "사칙연산(+, -, *, /)과 괄호만 허용됩니다."
        )
        form_layout.addRow("사용자 정의 식:", self.lineEdit_formula)

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
        saved_formula = settings.get_custom_formula()

        if saved_exe and Path(saved_exe).is_file():
            self.lineEdit_exe.setText(saved_exe)
        if saved_rch and Path(saved_rch).is_file():
            self.lineEdit_rch.setText(saved_rch)
        if saved_cio and Path(saved_cio).is_file():
            self.lineEdit_cio.setText(saved_cio)
        if saved_formula:
            self.lineEdit_formula.setText(saved_formula)

    def _save_current_settings(self):
        """현재 입력된 경로 및 설정값 저장"""
        settings.set_converter_exe_path(self.lineEdit_exe.text().strip())
        settings.set_rch_path(self.lineEdit_rch.text().strip())
        settings.set_cio_path(self.lineEdit_cio.text().strip())
        settings.set_custom_formula(self.lineEdit_formula.text().strip())

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
        formula = self.lineEdit_formula.text().strip()

        if not exe_path:
            QMessageBox.warning(
                self, "입력 오류", "SWAT-K Converter 프로그램(.exe)을 지정해주세요."
            )
            return

        if not Path(exe_path).is_file():
            QMessageBox.warning(
                self,
                "파일 오류",
                "지정된 Converter 프로그램(.exe)이 존재하지 않습니다.",
            )
            return

        if not rch_path:
            QMessageBox.warning(self, "입력 오류", "RCH 파일을 지정해주세요.")
            return

        if not Path(rch_path).is_file():
            QMessageBox.warning(
                self, "파일 오류", "지정된 RCH 파일이 존재하지 않습니다."
            )
            return

        if not cio_path:
            QMessageBox.warning(self, "입력 오류", "CIO 파일을 지정해주세요.")
            return

        if not Path(cio_path).is_file():
            QMessageBox.warning(
                self, "파일 오류", "지정된 CIO 파일이 존재하지 않습니다."
            )
            return

        is_valid, err_msg = validate_formula(formula)
        if not is_valid:
            QMessageBox.warning(self, "수식 입력 오류", err_msg)
            return

        # 설정값 영속화
        self._save_current_settings()

        info_msg = (
            "SWAT-K Converter 연동 기능은 현재 개발 중입니다.\n\n"
            f"• 지정된 실행 파일:\n  {exe_path}\n"
            f"• RCH 파일:\n  {rch_path}\n"
            f"• CIO 파일:\n  {cio_path}\n"
            f"• 사용자 정의 식:\n  {formula}"
        )
        QMessageBox.information(self, "안내", info_msg)
