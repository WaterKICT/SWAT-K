"""SWAT-K 로깅 및 QGIS 알림 메시지 통합 유틸리티 모듈

QGIS 공식 플러그인 가이드라인에 따라:
- QgsMessageLog를 통해 QGIS 로그 패널에 이벤트 기록
- iface.messageBar()를 통한 비차단형 상단 알림 메시지 출력
- QMessageBox를 통한 사용자 작업 실패 시 모달 대화상자 알림 지원
- QGIS 비의존성 테스트 환경에서도 콘솔로 안전하게 폴백
"""

import sys

try:
    from qgis.core import Qgis, QgsMessageLog
except ImportError:
    Qgis = None
    QgsMessageLog = None

try:
    from qgis.PyQt.QtWidgets import QMessageBox
except ImportError:
    try:
        from PySide6.QtWidgets import QMessageBox
    except ImportError:
        QMessageBox = None

PLUGIN_TAG = "SWAT-K"


def _get_message_level(level_name: str):
    """Qgis.MessageLevel 열거형 값을 안전하게 반환합니다."""
    if not Qgis:
        return 0
    name = level_name.lower()
    if hasattr(Qgis, "MessageLevel"):
        mapping = {
            "info": Qgis.MessageLevel.Info,
            "warning": Qgis.MessageLevel.Warning,
            "critical": Qgis.MessageLevel.Critical,
            "success": Qgis.MessageLevel.Success,
        }
        return mapping.get(name, Qgis.MessageLevel.Info)
    # 구버전 QGIS 호환
    mapping = {
        "info": getattr(Qgis, "Info", 0),
        "warning": getattr(Qgis, "Warning", 1),
        "critical": getattr(Qgis, "Critical", 2),
        "success": getattr(Qgis, "Success", 3),
    }
    return mapping.get(name, 0)


def log_info(message: str, tag: str = PLUGIN_TAG) -> None:
    """정보 로그를 QGIS MessageLog 패널에 기록합니다."""
    if QgsMessageLog and Qgis:
        QgsMessageLog.logMessage(str(message), tag, _get_message_level("info"))
    else:
        print(f"[{tag}] [INFO] {message}", file=sys.stdout)


def log_warning(message: str, tag: str = PLUGIN_TAG) -> None:
    """경고 로그를 QGIS MessageLog 패널에 기록합니다."""
    if QgsMessageLog and Qgis:
        QgsMessageLog.logMessage(str(message), tag, _get_message_level("warning"))
    else:
        print(f"[{tag}] [WARNING] {message}", file=sys.stderr)


def log_error(message: str, tag: str = PLUGIN_TAG) -> None:
    """오류 로그를 QGIS MessageLog 패널에 기록합니다."""
    if QgsMessageLog and Qgis:
        QgsMessageLog.logMessage(str(message), tag, _get_message_level("critical"))
    else:
        print(f"[{tag}] [ERROR] {message}", file=sys.stderr)


def notify_user(
    iface,
    title: str,
    message: str,
    level: str = "info",
    duration: int = 5,
) -> None:
    """QGIS 상단 알림 바(QgsMessageBar)에 알림 메시지를 표시하고 로그를 기록합니다.

    Args:
        iface: QGIS QgisInterface 객체 (None인 경우 로깅만 수행)
        title: 알림 제목
        message: 알림 본문
        level: "info" | "warning" | "critical" | "success"
        duration: 표시 유지 시간(초), 0이면 닫을 때까지 유지
    """
    if level == "critical":
        log_error(f"{title}: {message}")
    elif level == "warning":
        log_warning(f"{title}: {message}")
    else:
        log_info(f"{title}: {message}")

    if iface and hasattr(iface, "messageBar"):
        bar = iface.messageBar()
        if bar:
            bar.pushMessage(
                title,
                message,
                level=_get_message_level(level),
                duration=duration,
            )


def show_error_message(parent, title: str, message: str) -> None:
    """모달 오류 대화상자(QMessageBox)를 띄우고 동시에 로그를 남깁니다."""
    log_error(f"{title}: {message}")
    if QMessageBox:
        QMessageBox.critical(parent, title, str(message))


def show_warning_message(parent, title: str, message: str) -> None:
    """모달 경고 대화상자(QMessageBox)를 띄우고 동시에 로그를 남깁니다."""
    log_warning(f"{title}: {message}")
    if QMessageBox:
        QMessageBox.warning(parent, title, str(message))


def show_info_message(parent, title: str, message: str) -> None:
    """모달 정보 대화상자(QMessageBox)를 띄우고 동시에 로그를 남깁니다."""
    log_info(f"{title}: {message}")
    if QMessageBox:
        QMessageBox.information(parent, title, str(message))
