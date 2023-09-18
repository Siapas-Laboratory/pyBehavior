import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QDialog, QListWidget, QDialogButtonBox
from pathlib import Path
from pyBehavior.map_editor import *


class SetupSelectDialog(QDialog):
    def __init__(self, setup_dir):
        super(SetupSelectDialog, self).__init__()
        setups = []
        for x in Path(setup_dir).iterdir():
            if x.is_dir():
                if 'gui.py' in [j.name for j in x.iterdir()]:
                    setups.append(x.name)
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

    def __init__(self, setup_dir):
        super(MainWindow, self).__init__()
        self.setup_dir = setup_dir
        sys.path.append(setup_dir)
        # create settings button
        self.setWindowTitle("My App")
        self.settings_btn = QPushButton("Edit Mappings")
        self.settings_dialog = Settings(self.setup_dir) # instantiate settings dialog window
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
        dialog = SetupSelectDialog(self.setup_dir)
        res = dialog.exec_()
        if res:
            setup = dialog.setup_select.currentItem().text()
            import importlib
            setup_mod = importlib.import_module(f'{setup}.gui')
            setup_GUI = getattr(setup_mod, setup)
            self.setup_GUI = setup_GUI()
            self.setup_GUI.show()


if __name__ == '__main__':
    app = QApplication([])

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup_dir', required = True)
    args = parser.parse_args()

    window = MainWindow(args.setup_dir)
    window.show()

    app.exec()