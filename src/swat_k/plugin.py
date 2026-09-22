"""SWAT-K QGIS 플러그인 메인 모듈"""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .run_window import RunDialog
from .view_window import ViewDialog


class SwatKPlugin:
    """SWAT-K QGIS 플러그인 클래스"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.run_dialog = None
        self.view_dialog = None

    def initGui(self):
        """QGIS GUI 초기화: 풀다운 메뉴 없이 2개의 툴바 아이콘 등록"""
        icon_run_path = os.path.join(self.plugin_dir, "icon_run.png")
        if not os.path.isfile(icon_run_path):
            icon_run_path = os.path.join(self.plugin_dir, "icon_run.svg")

        icon_view_path = os.path.join(self.plugin_dir, "icon_view.png")
        if not os.path.isfile(icon_view_path):
            icon_view_path = os.path.join(self.plugin_dir, "icon_view.svg")

        # 1. [SWAT-K] Run 액션 등록
        self.action_run = QAction(
            QIcon(icon_run_path),
            "[SWAT-K] Run",
            self.iface.mainWindow(),
        )
        self.action_run.triggered.connect(self.run_converter)
        self.iface.addToolBarIcon(self.action_run)
        self.actions.append(self.action_run)

        # 2. [SWAT-K] View 액션 등록
        self.action_view = QAction(
            QIcon(icon_view_path),
            "[SWAT-K] View",
            self.iface.mainWindow(),
        )
        self.action_view.triggered.connect(self.open_view)
        self.iface.addToolBarIcon(self.action_view)
        self.actions.append(self.action_view)

    def unload(self):
        """플러그인 언로드 시 등록된 툴바 아이콘 해제"""
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        self.actions.clear()

        if self.run_dialog:
            self.run_dialog.close()
            self.run_dialog = None

        if self.view_dialog:
            self.view_dialog.close()
            self.view_dialog = None

    def run_converter(self):
        """[SWAT-K] Run 대화상자 열기"""
        if not self.run_dialog:
            self.run_dialog = RunDialog(self.iface.mainWindow(), iface=self.iface)
        self.run_dialog.show()
        self.run_dialog.raise_()
        self.run_dialog.activateWindow()

    def open_view(self):
        """[SWAT-K] View 대화상자 열기"""
        if not self.view_dialog:
            self.view_dialog = ViewDialog(self.iface.mainWindow(), iface=self.iface)
        else:
            self.view_dialog.refresh_from_settings()
        self.view_dialog.show()
        self.view_dialog.raise_()
        self.view_dialog.activateWindow()
