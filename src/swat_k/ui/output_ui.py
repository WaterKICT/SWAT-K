# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'output.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(500, 813)
        self.verticalLayout_Main = QVBoxLayout(Form)
        self.verticalLayout_Main.setObjectName(u"verticalLayout_Main")
        self.groupBox_Input = QGroupBox(Form)
        self.groupBox_Input.setObjectName(u"groupBox_Input")
        self.verticalLayout_Input = QVBoxLayout(self.groupBox_Input)
        self.verticalLayout_Input.setObjectName(u"verticalLayout_Input")
        self.formLayout_Input = QFormLayout()
        self.formLayout_Input.setObjectName(u"formLayout_Input")
        self.label_rch = QLabel(self.groupBox_Input)
        self.label_rch.setObjectName(u"label_rch")

        self.formLayout_Input.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_rch)

        self.horizontalLayout_rch = QHBoxLayout()
        self.horizontalLayout_rch.setObjectName(u"horizontalLayout_rch")
        self.lineEdit_rch = QLineEdit(self.groupBox_Input)
        self.lineEdit_rch.setObjectName(u"lineEdit_rch")

        self.horizontalLayout_rch.addWidget(self.lineEdit_rch)

        self.button_browse_rch = QPushButton(self.groupBox_Input)
        self.button_browse_rch.setObjectName(u"button_browse_rch")

        self.horizontalLayout_rch.addWidget(self.button_browse_rch)


        self.formLayout_Input.setLayout(0, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_rch)

        self.label_cio = QLabel(self.groupBox_Input)
        self.label_cio.setObjectName(u"label_cio")

        self.formLayout_Input.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_cio)

        self.horizontalLayout_cio = QHBoxLayout()
        self.horizontalLayout_cio.setObjectName(u"horizontalLayout_cio")
        self.lineEdit_cio = QLineEdit(self.groupBox_Input)
        self.lineEdit_cio.setObjectName(u"lineEdit_cio")

        self.horizontalLayout_cio.addWidget(self.lineEdit_cio)

        self.button_browse_cio = QPushButton(self.groupBox_Input)
        self.button_browse_cio.setObjectName(u"button_browse_cio")

        self.horizontalLayout_cio.addWidget(self.button_browse_cio)


        self.formLayout_Input.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_cio)

        self.label_year = QLabel(self.groupBox_Input)
        self.label_year.setObjectName(u"label_year")

        self.formLayout_Input.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_year)

        self.lineEdit_year = QLineEdit(self.groupBox_Input)
        self.lineEdit_year.setObjectName(u"lineEdit_year")

        self.formLayout_Input.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lineEdit_year)


        self.verticalLayout_Input.addLayout(self.formLayout_Input)

        self.button_convert = QPushButton(self.groupBox_Input)
        self.button_convert.setObjectName(u"button_convert")

        self.verticalLayout_Input.addWidget(self.button_convert)


        self.verticalLayout_Main.addWidget(self.groupBox_Input)

        self.groupBox_Output = QGroupBox(Form)
        self.groupBox_Output.setObjectName(u"groupBox_Output")
        self.verticalLayout_Output = QVBoxLayout(self.groupBox_Output)
        self.verticalLayout_Output.setObjectName(u"verticalLayout_Output")
        self.button_read_result = QPushButton(self.groupBox_Output)
        self.button_read_result.setObjectName(u"button_read_result")

        self.verticalLayout_Output.addWidget(self.button_read_result)

        self.line = QFrame(self.groupBox_Output)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_Output.addWidget(self.line)

        self.label_title_daily_flow = QLabel(self.groupBox_Output)
        self.label_title_daily_flow.setObjectName(u"label_title_daily_flow")

        self.verticalLayout_Output.addWidget(self.label_title_daily_flow)

        self.label_chart_daily_flow = QLabel(self.groupBox_Output)
        self.label_chart_daily_flow.setObjectName(u"label_chart_daily_flow")
        self.label_chart_daily_flow.setMinimumSize(QSize(0, 200))
        self.label_chart_daily_flow.setStyleSheet(u"background-color: #f0f0f0; border: 1px solid #ccc;")
        self.label_chart_daily_flow.setAlignment(Qt.AlignCenter)

        self.verticalLayout_Output.addWidget(self.label_chart_daily_flow)

        self.label_title_flow_duration = QLabel(self.groupBox_Output)
        self.label_title_flow_duration.setObjectName(u"label_title_flow_duration")

        self.verticalLayout_Output.addWidget(self.label_title_flow_duration)

        self.label_chart_flow_duration = QLabel(self.groupBox_Output)
        self.label_chart_flow_duration.setObjectName(u"label_chart_flow_duration")
        self.label_chart_flow_duration.setMinimumSize(QSize(0, 200))
        self.label_chart_flow_duration.setStyleSheet(u"background-color: #f0f0f0; border: 1px solid #ccc;")
        self.label_chart_flow_duration.setAlignment(Qt.AlignCenter)

        self.verticalLayout_Output.addWidget(self.label_chart_flow_duration)

        self.label_title_peak_flow = QLabel(self.groupBox_Output)
        self.label_title_peak_flow.setObjectName(u"label_title_peak_flow")

        self.verticalLayout_Output.addWidget(self.label_title_peak_flow)

        self.formLayout_Results = QFormLayout()
        self.formLayout_Results.setObjectName(u"formLayout_Results")
        self.label_max_flow_title = QLabel(self.groupBox_Output)
        self.label_max_flow_title.setObjectName(u"label_max_flow_title")

        self.formLayout_Results.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_max_flow_title)

        self.label_max_flow_value = QLabel(self.groupBox_Output)
        self.label_max_flow_value.setObjectName(u"label_max_flow_value")

        self.formLayout_Results.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_max_flow_value)

        self.label_peak_flow_title = QLabel(self.groupBox_Output)
        self.label_peak_flow_title.setObjectName(u"label_peak_flow_title")

        self.formLayout_Results.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_peak_flow_title)

        self.label_peak_flow_value = QLabel(self.groupBox_Output)
        self.label_peak_flow_value.setObjectName(u"label_peak_flow_value")

        self.formLayout_Results.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_peak_flow_value)


        self.verticalLayout_Output.addLayout(self.formLayout_Results)


        self.verticalLayout_Main.addWidget(self.groupBox_Output)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_Main.addItem(self.verticalSpacer)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"KICT SWAT PoC 2025", None))
        self.groupBox_Input.setTitle(QCoreApplication.translate("Form", u"Input", None))
        self.label_rch.setText(QCoreApplication.translate("Form", u"RCH file \uc9c0\uc815:", None))
        self.lineEdit_rch.setText(QCoreApplication.translate("Form", u"output_daily.rch", None))
        self.button_browse_rch.setText(QCoreApplication.translate("Form", u"\ucc3e\uc544\ubcf4\uae30...", None))
        self.label_cio.setText(QCoreApplication.translate("Form", u"CIO file \uc9c0\uc815:", None))
        self.lineEdit_cio.setText(QCoreApplication.translate("Form", u"file.cio", None))
        self.button_browse_cio.setText(QCoreApplication.translate("Form", u"\ucc3e\uc544\ubcf4\uae30...", None))
        self.label_year.setText(QCoreApplication.translate("Form", u"start year:", None))
        self.lineEdit_year.setText(QCoreApplication.translate("Form", u"1980", None))
        self.button_convert.setText(QCoreApplication.translate("Form", u"convert", None))
        self.groupBox_Output.setTitle(QCoreApplication.translate("Form", u"output \uc694\uc18c (POC\ub294 RCH1, 1980\ub144\uc5d0 \ub300\ud558\uc5ec \uc218\ud589)", None))
        self.button_read_result.setText(QCoreApplication.translate("Form", u"read result", None))
        self.label_title_daily_flow.setText(QCoreApplication.translate("Form", u"\uc77c\ub2e8\uc704 \uc720\ub7c9 \ucc60\ud2b8", None))
        self.label_chart_daily_flow.setText(QCoreApplication.translate("Form", u"\uc77c\ub2e8\uc704 \uc720\ub7c9 \ucc60\ud2b8 (PNG/Chart Placeholder)", None))
        self.label_title_flow_duration.setText(QCoreApplication.translate("Form", u"\uc18c\uc720\uc5ed\ubcc4 \uc5f0\ub3c4\ubcc4 \uc720\ud669\uace1\uc120", None))
        self.label_chart_flow_duration.setText(QCoreApplication.translate("Form", u"\uc720\ud669\uace1\uc120 (PNG/Chart Placeholder)", None))
        self.label_title_peak_flow.setText(QCoreApplication.translate("Form", u"\uc18c\uc720\uc5ed\ubcc4 \uc5f0\ub3c4\ubcc4 \ucd5c\ub300\ud64d\uc218\ub7c9 \ubc0f \ucca8\ub450\ud64d\uc218\ub7c9", None))
        self.label_max_flow_title.setText(QCoreApplication.translate("Form", u"\ucd5c\ub300\ud64d\uc218\ub7c9 :", None))
        self.label_max_flow_value.setText(QCoreApplication.translate("Form", u"92.77", None))
        self.label_peak_flow_title.setText(QCoreApplication.translate("Form", u"\ucca8\ub450\ud64d\uc218\ub7c9 :", None))
        self.label_peak_flow_value.setText(QCoreApplication.translate("Form", u"105.787", None))
    # retranslateUi

