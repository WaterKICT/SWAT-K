import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

try:
    from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
    from qgis.PyQt.QtGui import QIcon
    from qgis.PyQt.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )
except ImportError:
    from PySide6.QtCore import Qt, QThread
    from PySide6.QtCore import Signal as pyqtSignal
    from PySide6.QtCore import Slot as pyqtSlot
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QDialog,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

from swat_k.core.formula import DEFAULT_FORMULA, validate_formula
from swat_k.utils import settings
from swat_k.utils.logger import (
    log_warning,
    notify_user,
    show_error_message,
    show_info_message,
    show_warning_message,
)


class ConverterWorker(QThread):
    """외부 Converter 프로그램을 독립 콘솔 창에서 비동기로 실행하는 워커 스레드"""

    finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(
        self,
        exe_path: str,
        arguments: list[str],
        working_dir: str,
        parent=None,
    ):
        super().__init__(parent)
        self.exe_path = exe_path
        self.arguments = arguments
        self.working_dir = working_dir
        self._process = None
        self._bat_file = None

    def run(self):
        try:
            # cmd.exe 기반 런처 배치 파일 생성:
            # 1. cmd.exe가 표준 입출력(CONOUT$)을 활성 콘솔 버퍼에 정상 바인딩
            # 2. 오류 발생 시 창이 바로 꺼지지 않고 일시정지(pause)
            timestamp = int(time.time() * 1000)
            self._bat_file = Path(tempfile.gettempdir()) / f"swat_k_run_{timestamp}.bat"

            args_str = " ".join(f'"{arg}"' for arg in self.arguments)
            bat_content = (
                "@echo off\r\n"
                "chcp 65001 > nul\r\n"
                "title SWAT-K Converter\r\n"
                f'cd /d "{self.working_dir}"\r\n'
                f'"{self.exe_path}" {args_str}\r\n'
                "set EXIT_CODE=%ERRORLEVEL%\r\n"
                "if %EXIT_CODE% equ 0 goto SUCCESS\r\n"
                "goto FAILED\r\n"
                "\r\n"
                ":SUCCESS\r\n"
                "echo.\r\n"
                "echo [완료] 변환 작업이 완료되었습니다. (2초 후 자동으로 닫힙니다)\r\n"
                "timeout /t 2 > nul\r\n"
                "exit /b 0\r\n"
                "\r\n"
                ":FAILED\r\n"
                "echo.\r\n"
                "echo =======================================================\r\n"
                "echo [오류] 변환 실패 (종료 코드: %EXIT_CODE%)\r\n"
                "echo 메시지 확인 후 창을 닫으려면 아무 키나 누르세요...\r\n"
                "echo =======================================================\r\n"
                "pause > nul\r\n"
                "exit /b %EXIT_CODE%\r\n"
            )
            self._bat_file.write_text(bat_content, encoding="utf-8")

            cmd_exe = (
                os.environ.get("COMSPEC")
                or shutil.which("cmd.exe")
                or r"C:\Windows\System32\cmd.exe"
            )
            # 안전하게 생성된 임시 .bat 파일을 시스템 shell로 실행
            self._process = subprocess.Popen(  # nosec B603, B607 # noqa: S603, S607
                [cmd_exe, "/c", str(self._bat_file.resolve())],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=self.working_dir,
            )
            exit_code = self._process.wait()
            self.finished_signal.emit(exit_code)
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            if self._bat_file and self._bat_file.exists():
                try:
                    self._bat_file.unlink(missing_ok=True)
                except OSError as e:
                    log_warning(f"임시 배치 파일({self._bat_file}) 삭제 실패: {e}")

    def terminate_process(self):
        """프로세스 안전 종료"""
        if self._process and self._process.poll() is None:
            try:
                self._process.kill()
            except OSError as e:
                log_warning(f"Converter 프로세스 강제 종료 실패: {e}")


class RunDialog(QDialog):
    """SWAT-K Converter 실행 설정 및 입력 파일 지정 대화상자"""

    def __init__(self, parent=None, iface=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("[SWAT-K] Run - Converter 실행")
        icon_path = Path(__file__).parent / "icon.png"
        if not icon_path.is_file():
            icon_path = Path(__file__).parent / "icon.svg"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.resize(660, 320)
        self.worker: ConverterWorker | None = None
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
        self.lineEdit_rch.setPlaceholderText("RCH 파일 경로를 선택하세요 (*.rch)")
        self.btn_browse_rch = QPushButton("찾아보기...", self)
        self.btn_browse_rch.clicked.connect(self._browse_rch_file)

        layout_rch = QHBoxLayout()
        layout_rch.addWidget(self.lineEdit_rch)
        layout_rch.addWidget(self.btn_browse_rch)
        form_layout.addRow("RCH 파일 경로:", layout_rch)

        # CIO 파일 경로 선택
        self.lineEdit_cio = QLineEdit(self)
        self.lineEdit_cio.setPlaceholderText("CIO 파일 경로를 선택하세요 (*.cio)")
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

        # 2. 실행 상태 라벨
        self.label_status = QLabel("", self)
        self.label_status.setStyleSheet("font-size: 11px;")
        main_layout.addWidget(self.label_status)

        # 3. 하단 실행 및 닫기 버튼
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
        rch_text = self.lineEdit_rch.text().strip()
        settings.set_rch_path(rch_text)
        if rch_text:
            settings.set_data_dir(str(Path(rch_text).parent))
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
            "RCH 파일 (*.rch);;모든 파일 (*)",
        )
        if file_path:
            if file_path.lower().endswith(".csv"):
                QMessageBox.warning(
                    self,
                    "파일 선택 오류",
                    "CSV 파일은 선택할 수 없습니다. RCH 파일(*.rch)을 선택해주세요.",
                )
                return
            self.lineEdit_rch.setText(file_path)
            settings.set_rch_path(file_path)
            settings.set_data_dir(str(Path(file_path).parent))

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
            "CIO 파일 (*.cio);;모든 파일 (*)",
        )
        if file_path:
            if file_path.lower().endswith(".csv"):
                QMessageBox.warning(
                    self,
                    "파일 선택 오류",
                    "CSV 파일은 선택할 수 없습니다. CIO 파일(*.cio)을 선택해주세요.",
                )
                return
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

        if rch_path.lower().endswith(".csv"):
            show_warning_message(
                self,
                "파일 형식 오류",
                "CSV 파일은 RCH 입력으로 사용할 수 없습니다.\n"
                "*.rch 파일을 선택해주세요.",
            )
            return

        if not cio_path:
            show_warning_message(self, "입력 오류", "CIO 파일을 지정해주세요.")
            return

        if not Path(cio_path).is_file():
            show_warning_message(
                self, "파일 오류", "지정된 CIO 파일이 존재하지 않습니다."
            )
            return

        if cio_path.lower().endswith(".csv"):
            show_warning_message(
                self,
                "파일 형식 오류",
                "CSV 파일은 CIO 입력으로 사용할 수 없습니다.\n"
                "*.cio 파일을 선택해주세요.",
            )
            return

        is_valid, err_msg = validate_formula(formula)
        if not is_valid:
            QMessageBox.warning(self, "수식 입력 오류", err_msg)
            return

        # 설정값 영속화
        self._save_current_settings()
        settings.set_data_dir(str(Path(rch_path).parent))

        # Converter CLI 실행 인자: <rch_path> <cio_path> "<formula>"
        arguments = [rch_path, cio_path, formula]
        working_dir = str(Path(exe_path).parent)

        # UI 상태 업데이트 (실행 중 표시)
        self.btn_run.setEnabled(False)
        self.btn_run.setText("변환 작업 진행 중...")
        self.label_status.setText(
            "Converter 콘솔 창에서 데이터 변환이 진행 중입니다..."
        )
        self.label_status.setStyleSheet("color: #2563EB; font-weight: bold;")

        # 백그라운드 워커 스레드 시작 (새 콘솔 창 생성으로 커서 조작 예외 방지)
        self.worker = ConverterWorker(exe_path, arguments, working_dir, parent=self)
        self.worker.finished_signal.connect(self._on_conversion_finished)
        self.worker.error_signal.connect(self._on_conversion_error)
        self.worker.start()

    @pyqtSlot(int)
    def _on_conversion_finished(self, exit_code: int):
        """Converter 프로세스 종료 시 슬롯"""
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Converter 실행")

        if exit_code == 0:
            rch_path = self.lineEdit_rch.text().strip()
            folder_info = ""
            if rch_path and Path(rch_path).is_file():
                parent_dir = Path(rch_path).parent
                latest_out = settings.find_latest_out_dir(parent_dir)
                if latest_out:
                    settings.set_data_dir(str(latest_out))
                    folder_info = f"\n(결과 폴더: {latest_out.name})"
                else:
                    settings.set_data_dir(str(parent_dir))
            elif rch_path and Path(rch_path).parent.is_dir():
                settings.set_data_dir(str(Path(rch_path).parent))

            self.label_status.setText(
                f"변환 작업이 성공적으로 완료되었습니다.{folder_info}"
            )
            self.label_status.setStyleSheet("color: #16A34A; font-weight: bold;")

            msg = (
                f"SWAT-K Converter 변환 작업이 성공적으로 완료되었습니다.{folder_info}"
            )
            notify_user(self.iface, "SWAT-K 변환 완료", msg, level="success")
            show_info_message(self, "변환 완료", msg)
        else:
            err_msg = f"Converter 실행 중 오류가 발생했습니다 (종료 코드: {exit_code})."
            self.label_status.setText(
                f"변환 작업 중 오류가 발생했습니다 (종료 코드: {exit_code})."
            )
            self.label_status.setStyleSheet("color: #DC2626; font-weight: bold;")
            notify_user(self.iface, "SWAT-K 변환 오류", err_msg, level="critical")
            show_error_message(self, "변환 오류", err_msg)

    @pyqtSlot(str)
    def _on_conversion_error(self, error_msg: str):
        """프로세스 실행 실패 슬롯"""
        self.btn_run.setEnabled(True)
        self.btn_run.setText("Converter 실행")
        self.label_status.setText("변환 실행 중 오류가 발생했습니다.")
        self.label_status.setStyleSheet("color: #DC2626; font-weight: bold;")
        detail_msg = (
            f"Converter 프로세스를 실행하는 중 오류가 발생했습니다:\n{error_msg}"
        )
        notify_user(self.iface, "SWAT-K 실행 오류", detail_msg, level="critical")
        show_error_message(self, "실행 오류", detail_msg)

    def closeEvent(self, event):
        """대화상자 닫기 시 실행 중인 프로세스 확인"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "작업 중단 확인",
                "변환 작업이 아직 실행 중입니다. 중단하고 창을 닫으시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate_process()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
