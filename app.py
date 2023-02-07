import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QDialog, QListWidget, QDialogButtonBox
from PyQt5.QtCore import Qt
import numpy as np
from pathlib import Path
from map_editor import *


class SetupSelectDialog(QDialog):
    def __init__(self):
        super(SetupSelectDialog, self).__init__()
        setups = [x.name for x in Path('setups').iterdir() if x.is_dir()]

        layout = QVBoxLayout()
        self.setup_select = QListWidget()
        self.setup_select.addItems(setups)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout.addWidget(self.setup_select)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        # create settings button
        self.setWindowTitle("My App")
        self.settings_btn = QPushButton("Edit Mappings")
        self.settings_dialog = Settings() # instantiate settings dialog window
        self.settings_btn.clicked.connect(self.open_settings_dialog)


        self.setup_btn = QPushButton("Select Setup")
        self.setup_btn.clicked.connect(self.open_setup_dialog)

        layout = QVBoxLayout()
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.setup_btn)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def open_settings_dialog(self):
        self.settings_dialog.show()

    def open_setup_dialog(self):
        dialog = SetupSelectDialog()
        dialog.exec_()
        # should check if they clicked ok first
        setup = dialog.setup_select.currentItem().text()
        import importlib
        setup_mod = importlib.import_module(f'setups.{setup}.visualizer')
        Visualizer = getattr(setup_mod, setup)
        self.visualizer = Visualizer()
        self.visualizer.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()