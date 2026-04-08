# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QVBoxLayout

from .main_window import MainWindow

class SwatKPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "SWAT-K"
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.svg')
        
        self.action = QAction(
            QIcon(icon_path),
            "Run SWAT-K",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        
        # Add to the Plugins menu
        self.iface.addPluginToMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)
        self.actions.append(self.action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        if not self.dialog:
            self.dialog = QDialog(self.iface.mainWindow())
            self.dialog.setWindowTitle("SWAT-K PoC 2025")
            layout = QVBoxLayout(self.dialog)
            
            # Instantiate the existing MainWindow widget
            self.main_widget = MainWindow()
            layout.addWidget(self.main_widget)
            
            # Adjust size and make it properly expand
            self.dialog.resize(900, 800)
            
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
