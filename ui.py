from PySide2.QtWidgets import (QDialog, QWidget, QPushButton, QVBoxLayout,
                               QLineEdit, QLabel,QHBoxLayout, QComboBox,
                               QCheckBox, QSlider)
from PySide2.QtCore import Qt

import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance

from . import rig_utils

import importlib
importlib.reload(rig_utils)

import sys
import os

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.append(parent_dir)

def mayaMainWindow():
    mainWindowPtr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(mainWindowPtr),QWidget)

def showUI():
    global mihoyo_tool_win

    try:
        mihoyo_tool_win.close()
        mihoyo_tool_win.deleteLater()
    except:
        pass

    mihoyo_tool_win = MainWindow()
    mihoyo_tool_win.show()

class MainWindow(QDialog):
    def __init__(self, parent = mayaMainWindow()):
        super(MainWindow, self).__init__(parent)

        self.setWindowTitle("Mihoyo_Tool")
        self.resize(200,200)

        # self.rig_data = None
        # add rig module
        self.rig_data = None
        self.rig_modules = {}
        self.current_module = None

        self.createWidget()
        self.createLayout()
        self.createConnections()


    def createWidget(self):
        # ikfk switch slider
        self.ikfkLabel = QLabel("IK/FK Switch")
        self.ikfkSlider = QSlider(Qt.Horizontal)
        self.ikfkSlider.setMinimum(0)
        self.ikfkSlider.setMaximum(10)
        self.ikfkSlider.setValue(0)

        # self.applyBtn = QPushButton("Apply")
        self.nameLable = QLabel("Name: ")
        self.nameLine = QLineEdit()
        self.nameLine.setPlaceholderText("example: arm_l")

        self.axisLabel = QLabel("Stretch Axis:")
        self.axisBox = QComboBox()
        self.axisBox.addItems(["X", "Y", "Z"])

        self.buildIKFKBtn = QPushButton("Build IKFK") #  build IKFK button
        self.addStretchBtn = QPushButton("Add Stretch") #  stretch button

        self.ikAlignFkBtn = QPushButton("IK Align FK")
        self.fkAlignIkBtn = QPushButton("FK Align IK")

        self.ikResetBtn = QPushButton("IK Reset")
        self.fkResetBtn = QPushButton("FK Reset")


        self.autoVisCheck = QCheckBox("Auto Vis")
        self.autoVisCheck.setChecked(True)

        self.ikVisCheck = QCheckBox("IK Vis")
        # self.ikVisCheck.setChecked(True)
        self.ikVisCheck.setEnabled(False)

        self.fkVisCheck = QCheckBox("FK Vis")
        # self.fkVisCheck.setChecked(True)
        self.fkVisCheck.setEnabled(False)

        # module box
        self.moduleLabel = QLabel("Current Module:")
        self.moduleBox = QComboBox()

    def createLayout(self):
        self.nameLayout = QHBoxLayout()
        #  so that the "name" and editline can in the same line
        self.nameLayout.addWidget(self.nameLable)
        self.nameLayout.addWidget(self.nameLine)

        self.moduleLayout = QHBoxLayout()
        self.moduleLayout.addWidget(self.moduleLabel)
        self.moduleLayout.addWidget(self.moduleBox)

        self.axisLayout = QHBoxLayout()
        self.axisLayout.addWidget(self.axisLabel)
        self.axisLayout.addWidget(self.axisBox)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addLayout(self.nameLayout)
        self.mainLayout.addLayout(self.moduleLayout) # add module layout
        self.mainLayout.addLayout(self.axisLayout)

        # add ikfkslider
        self.mainLayout.addWidget(self.ikfkLabel)
        self.mainLayout.addWidget(self.ikfkSlider)

        self.mainLayout.addWidget(self.buildIKFKBtn)
        self.mainLayout.addWidget(self.addStretchBtn)

        self.mainLayout.addWidget(self.ikAlignFkBtn)
        self.mainLayout.addWidget(self.fkAlignIkBtn)

        self.mainLayout.addWidget(self.ikResetBtn)
        self.mainLayout.addWidget(self.fkResetBtn)

        self.mainLayout.addWidget(self.autoVisCheck)
        self.mainLayout.addWidget(self.ikVisCheck)
        self.mainLayout.addWidget(self.fkVisCheck)

        self.setLayout(self.mainLayout)

    def createConnections(self):
        self.ikfkSlider.valueChanged.connect(self.applyIKFKSwitch)

        self.buildIKFKBtn.clicked.connect(self.applyBuildIKFK)
        self.addStretchBtn.clicked.connect(self.applyAddStretch)

        self.ikAlignFkBtn.clicked.connect(self.applyIKAlignFK)
        self.fkAlignIkBtn.clicked.connect(self.applyFKAlignIK)

        self.ikResetBtn.clicked.connect(self.applyIKReset)
        self.fkResetBtn.clicked.connect(self.applyFKReset)

        self.autoVisCheck.stateChanged.connect(self.applyAutoVisFromCheck)
        self.ikVisCheck.stateChanged.connect(self.applyIKVisFromCheck)
        self.fkVisCheck.stateChanged.connect(self.applyFKVisFromCheck)

        self.moduleBox.currentTextChanged.connect(self.applySwitchModule)

    def applyIKFKSwitch(self, value):
        if not self.checkRigData():
            return

        rig_utils.set_ikfk_value(self.rig_data, value)

    # def applyBuildIKFK(self):
    #     name = self.nameLine.text()
    #     if not name:
    #         name = "limb"
    #     self.rig_data = rig_utils.ikfkGenerator(name=name)
    #     print("Saved rig_data:", self.rig_data)
        # rig_utils.ikfkGenerator(name=self.nameLine.text())

    def applyBuildIKFK(self):
        name = self.nameLine.text()
        if not name:
            name = "limb"

        print("BUILD NAME:", name)
        self.rig_data = rig_utils.ikfkGenerator(name=name)

        self.rig_modules[name] = self.rig_data
        self.current_module = name

        print("ALL MODULES:", self.rig_modules.keys())

        if self.moduleBox.findText(name) == -1:
            print("ADD MODULE TO BOX:", name)
            self.moduleBox.addItem(name)
        else:
            print("MODULE ALREADY IN BOX:", name)
        # for debug
        index = self.moduleBox.findText(name)
        print("MODULE INDEX:", index)
        if index != -1:
            self.moduleBox.setCurrentIndex(index)

        # self.moduleBox.setCurrentText(name)


        # print("Saved rig_data:", self.rig_data)
        print("Current module:", self.current_module)

    def applyAddStretch(self):
        if not self.checkRigData():
            return

        axis = self.axisBox.currentText()
        rig_utils.addStretch(self.rig_data, axis=axis)

    def applyIKAlignFK(self):
        if not self.checkRigData():
            return
        rig_utils.ik_align_fk(self.rig_data)

    def applyFKAlignIK(self):
        if not self.checkRigData():
            return
        rig_utils.fk_align_ik(self.rig_data)

    def applyIKReset(self):
        if not self.checkRigData():
            return
        rig_utils.ik_reset(self.rig_data)

    def applyFKReset(self):
        if not self.checkRigData():
            return
        rig_utils.fk_reset(self.rig_data)

    def applyAutoVisFromCheck(self):
        if not self.checkRigData():
            return

        value = self.autoVisCheck.isChecked()
        rig_utils.set_auto_vis(self.rig_data, value)

        self.ikVisCheck.setEnabled(not value)
        self.fkVisCheck.setEnabled(not value)

    def applyIKVisFromCheck(self):
        if not self.checkRigData():
            return

        value = self.ikVisCheck.isChecked()
        rig_utils.set_ik_vis(self.rig_data, value)

    def applyFKVisFromCheck(self):
        if not self.checkRigData():
            return

        value = self.fkVisCheck.isChecked()
        rig_utils.set_fk_vis(self.rig_data, value)

    def checkRigData(self):
        if not self.current_module:
            print("Please build or select a module first.")
            return False

        if self.current_module not in self.rig_modules:
            print("Current module data is missing:", self.current_module)
            return False

        self.rig_data = self.rig_modules[self.current_module]
        return True

    def applySwitchModule(self, name):
        name = name.strip()
        if not name:
            return

        if name in self.rig_modules:
            self.current_module = name
            self.rig_data = self.rig_modules[name]
            print("Switched to module:", name)
        else:
            print("Module not found:", name)


ui = MainWindow()
ui.show()
