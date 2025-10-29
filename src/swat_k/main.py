"""애플리케이션 엔트리 포인트"""

import sys

from PySide6.QtWidgets import QApplication

from swat_k.main_window import MainWindow


def main():
    """메인 애플리케이션 실행"""
    app = QApplication(sys.argv)
    app.setApplicationName("KICT SWAT PoC 2025")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
