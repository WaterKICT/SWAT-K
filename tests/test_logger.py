"""SWAT-K 로깅 및 알림 유틸리티 단위 테스트"""

from io import StringIO
import sys
import unittest
from unittest.mock import MagicMock, patch

from swat_k.utils.logger import (
    log_error,
    log_info,
    log_warning,
    notify_user,
    show_error_message,
    show_info_message,
    show_warning_message,
)


class TestLogger(unittest.TestCase):
    """logger 모듈 기능 및 폴백 동작 검증"""

    def test_log_info_stdout_fallback(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            log_info("테스트 정보 메시지")
            self.assertIn("[SWAT-K] [INFO] 테스트 정보 메시지", fake_out.getvalue())

    def test_log_warning_stderr_fallback(self):
        with patch("sys.stderr", new=StringIO()) as fake_err:
            log_warning("테스트 경고 메시지")
            self.assertIn("[SWAT-K] [WARNING] 테스트 경고 메시지", fake_err.getvalue())

    def test_log_error_stderr_fallback(self):
        with patch("sys.stderr", new=StringIO()) as fake_err:
            log_error("테스트 오류 메시지")
            self.assertIn("[SWAT-K] [ERROR] 테스트 오류 메시지", fake_err.getvalue())

    def test_notify_user_with_mock_iface(self):
        mock_iface = MagicMock()
        mock_bar = MagicMock()
        mock_iface.messageBar.return_value = mock_bar

        notify_user(mock_iface, "알림 제목", "알림 본문", level="warning")
        mock_bar.pushMessage.assert_called_once()
        args, kwargs = mock_bar.pushMessage.call_args
        self.assertEqual(args[0], "알림 제목")
        self.assertEqual(args[1], "알림 본문")

    def test_dialog_helpers(self):
        with patch("swat_k.utils.logger.QMessageBox") as mock_box:
            show_info_message(None, "제목1", "메시지1")
            mock_box.information.assert_called_once_with(None, "제목1", "메시지1")

            show_warning_message(None, "제목2", "메시지2")
            mock_box.warning.assert_called_once_with(None, "제목2", "메시지2")

            show_error_message(None, "제목3", "메시지3")
            mock_box.critical.assert_called_once_with(None, "제목3", "메시지3")


if __name__ == "__main__":
    unittest.main()
