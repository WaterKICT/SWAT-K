"""SWAT-K Run 대화상자 단위 테스트"""

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from swat_k.run_window import RunDialog
from swat_k.utils import settings

app = QApplication.instance() or QApplication(sys.argv)


class TestRunDialog(unittest.TestCase):
    """RunDialog UI 및 shp 미사용 환경 검증"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)

        self.rch_file = self.tmppath / "output.rch"
        self.rch_file.touch()

        self.cio_file = self.tmppath / "file.cio"
        self.cio_file.touch()

        self.exe_file = self.tmppath / "converter.exe"
        self.exe_file.touch()

        settings.set_rch_path(str(self.rch_file))
        settings.set_cio_path(str(self.cio_file))
        settings.set_converter_exe_path(str(self.exe_file))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_run_dialog_init_without_shp_inputs(self):
        dialog = RunDialog()

        # 1. shp 관련 UI 요소가 존재하지 않는지 확인
        self.assertFalse(hasattr(dialog, "lineEdit_stream_shp"))
        self.assertFalse(hasattr(dialog, "lineEdit_subbasin_shp"))
        self.assertFalse(hasattr(dialog, "check_auto_add_layer"))

        # 2. 필수 Converter 입력 필드 확인
        self.assertEqual(dialog.lineEdit_exe.text(), str(self.exe_file))
        self.assertEqual(dialog.lineEdit_rch.text(), str(self.rch_file))
        self.assertEqual(dialog.lineEdit_cio.text(), str(self.cio_file))

        # 3. 설정값 저장 시 data_dir이 rch 부모 디렉터리로 설정되는지 확인
        dialog._save_current_settings()
        self.assertEqual(settings.get_data_dir(), str(self.tmppath))

    def test_reject_csv_inputs(self):
        from unittest.mock import patch

        dialog = RunDialog()

        # RCH로 .csv 파일이 지정된 경우
        csv_rch = self.tmppath / "output.csv"
        csv_rch.touch()
        dialog.lineEdit_rch.setText(str(csv_rch))
        dialog.lineEdit_cio.setText(str(self.cio_file))
        dialog.lineEdit_exe.setText(str(self.exe_file))

        with patch("swat_k.run_window.QMessageBox.warning") as mock_warn:
            dialog._on_run_clicked()
            self.assertIsNone(dialog.worker)
            mock_warn.assert_called()

        # CIO로 .csv 파일이 지정된 경우
        csv_cio = self.tmppath / "file.csv"
        csv_cio.touch()
        dialog.lineEdit_rch.setText(str(self.rch_file))
        dialog.lineEdit_cio.setText(str(csv_cio))

        with patch("swat_k.run_window.QMessageBox.warning") as mock_warn:
            dialog._on_run_clicked()
            self.assertIsNone(dialog.worker)
            mock_warn.assert_called()

        dialog.close()


if __name__ == "__main__":
    unittest.main()
