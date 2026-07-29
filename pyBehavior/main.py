import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QDialog, QListWidget, QDialogButtonBox,
                             QHBoxLayout, QComboBox, QLineEdit, QLabel, QScrollArea,
                             QGridLayout, QCheckBox, QInputDialog, QFrame)
from pathlib import Path
import numpy as np
import pandas as pd
import nidaqmx
import os
from pyBehavior import styles


class NewSetupDialog(QDialog):
    def __init__(self):
        super(NewSetupDialog, self).__init__()
        self.setWindowTitle("New Setup")
        self.fname = None

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("CREATE NEW SETUP")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {styles.ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {styles.BORDER_SUBTLE};")
        layout.addWidget(sep)

        # Name input
        name_label = QLabel("Setup name  (letters, numbers, underscores only)")
        layout.addWidget(name_label)
        self.fname_input = QLineEdit()
        self.fname_input.setPlaceholderText("e.g.  maze_rig_1")
        layout.addWidget(self.fname_input)

        # Hardware checkboxes
        hw_label = QLabel("HARDWARE")
        hw_label.setStyleSheet(f"color: {styles.ACCENT}; font-size: 16px; letter-spacing: 1px; margin-top: 6px;")
        layout.addWidget(hw_label)

        self.use_ni_cards = QCheckBox("National Instruments DAQ cards")
        self.use_rpi = QCheckBox("ratBerryPi reward interface")
        layout.addWidget(self.use_ni_cards)
        layout.addWidget(self.use_rpi)

        # RPI sub-panel (hidden initially)
        self.rpi_dialog = QWidget()
        rpi_dialog_layout = QVBoxLayout()
        rpi_dialog_layout.setSpacing(6)
        rpi_dialog_layout.setContentsMargins(0, 4, 0, 0)

        self.is_rpi_remote = QCheckBox("Connect to ratBerryPi remotely (SSH)")
        self.is_rpi_remote.setChecked(True)
        self.is_rpi_remote.stateChanged.connect(self.toggle_rpi_remote)
        rpi_dialog_layout.addWidget(self.is_rpi_remote)

        for attr, label in [('rpi_host', 'Host'), ('rpi_port', 'Port'), ('rpi_user', 'User')]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(40)
            le = QLineEdit()
            setattr(self, attr, le)
            row.addWidget(lbl)
            row.addWidget(le)
            rpi_dialog_layout.addLayout(row)

        self.rpi_dialog.setLayout(rpi_dialog_layout)
        self.rpi_dialog.setStyleSheet(f"QWidget {{ background: {styles.BG_SURFACE}; border-radius: 4px; padding: 4px; }}")
        self.rpi_dialog.hide()
        self.use_rpi.clicked.connect(self.show_rpi_dialog)
        layout.addWidget(self.rpi_dialog)

        # Buttons
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {styles.BORDER_SUBTLE};")
        layout.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel = QPushButton("Cancel")
        ok = QPushButton("Create Setup")
        ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.ACCENT_SOFT};
                color: {styles.ACCENT};
                border: 1px solid {styles.ACCENT};
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {styles.ACCENT_DIM}; color: {styles.BG_DEEP}; }}
        """)
        ok.clicked.connect(self.check_input)
        cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.setMinimumWidth(380)
        self.orig_size = self.minimumSizeHint()
        self.height = self.orig_size.height()
        self.width = self.orig_size.width()

    def toggle_rpi_remote(self):
        enabled = self.is_rpi_remote.isChecked()
        for attr in ('rpi_host', 'rpi_port', 'rpi_user'):
            getattr(self, attr).setEnabled(enabled)

    def show_rpi_dialog(self):
        if self.use_rpi.isChecked():
            self.rpi_dialog.show()
        else:
            self.rpi_dialog.hide()
        self.setMinimumSize(self.width, self.height)
        self.resize(self.minimumSizeHint())
        self.show()

    def check_input(self):
        self.fname = self.fname_input.text()
        valid = (len(self.fname) > 1) and all(x.isalnum() or x == "_" for x in self.fname)
        if valid:
            self.accept()


class Settings(QMainWindow):
    def __init__(self, root_dir):
        super(Settings, self).__init__()
        self.setWindowTitle("pyBehavior — Port Mappings")
        self.root_dir = root_dir

        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header_label = QLabel("PORT MAPPINGS")
        header_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {styles.ACCENT}; letter-spacing: 1.5px;")
        self.layout.addWidget(header_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {styles.BORDER_SUBTLE};")
        self.layout.addWidget(sep)

        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(6)

        available_mappings = []
        for i in Path(root_dir).iterdir():
            if i.is_dir():
                if 'port_map.csv' in [j.name for j in i.iterdir()]:
                    available_mappings.append(i.stem)

        self.map_file_select = QComboBox()
        self.map_file_select.addItems(available_mappings)
        if len(available_mappings) > 0:
            self.load_map()
        else:
            self.mapping = pd.DataFrame()

        self.map_file_select.currentIndexChanged.connect(self.change_map_file)
        self.header_layout.addWidget(self.map_file_select, stretch=3)

        self.create_btn = QPushButton("＋  New Setup")
        self.create_btn.clicked.connect(self.create)
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.ACCENT_SOFT};
                color: {styles.ACCENT};
                border: 1px solid {styles.ACCENT};
            }}
            QPushButton:hover {{ background-color: {styles.ACCENT_DIM}; color: {styles.BG_DEEP}; }}
        """)
        self.save_btn.clicked.connect(self.save)
        self.header_layout.addWidget(self.create_btn)
        self.header_layout.addWidget(self.save_btn)
        self.layout.addLayout(self.header_layout)

        # Column headers
        col_header = QHBoxLayout()
        for text in ("Address", "Friendly Name", "DI", ""):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {styles.ACCENT}; font-size: 16px; letter-spacing: 0.8px; font-weight: bold;")
            col_header.addWidget(lbl)
        self.layout.addLayout(col_header)

        # Scrollable body
        self.port_labels = []
        self.name_inputs = []
        self.di_select = []
        self.del_btns = []

        self.body_layout = QGridLayout()
        self.body_layout.setVerticalSpacing(4)
        self.fill_body()
        self.body_widget = QWidget()
        self.body_widget.setLayout(self.body_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.body_widget)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)

        # Footer buttons
        footer = QHBoxLayout()
        self.add_btn = QPushButton("＋  Add Row")
        self.add_btn.clicked.connect(self.add_map)
        self.get_btn = QPushButton("Scan All NI Ports")
        footer.addWidget(self.add_btn)
        footer.addWidget(self.get_btn)
        self.get_btn.clicked.connect(self.get_all_ports)
        self.layout.addLayout(footer)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
        self.resize(560, 480)

    @property
    def map_file(self):
        return os.path.join(self.root_dir, self.map_file_select.currentText(), 'port_map.csv')

    def load_map(self):
        self.mapping = pd.read_csv(self.map_file).set_index('port')
        self.mapping['name'] = self.mapping['name'].fillna("")
        if 'DI' not in self.mapping.columns:
            self.mapping['DI'] = [False] * len(self.mapping)

    def add_map(self):
        port, ok = QInputDialog().getText(self, "New Mapping", "Enter port address:")
        if ok:
            self.mapping.loc[port, 'name'] = ""
            self.mapping.loc[port, 'DI'] = False
            self.add_row(port, "", False)

    def fill_body(self):
        for port, data in self.mapping.T.items():
            self.add_row(port, data['name'], data['DI'])

    def scan_ports(self):
        from pyBehavior.interfaces.ni import daqmx_supported
        if daqmx_supported():
            system = nidaqmx.system.System.local()
            channels = []
            for dev in system.devices:
                channels += [i.name for i in dev.di_lines]
                channels += [i.name for i in dev.do_lines]
                channels += [i.name for i in dev.ai_physical_chans]
                channels += [i.name for i in dev.ao_physical_chans]
            return np.unique(channels).tolist()
        return []

    def get_all_ports(self):
        channels = self.scan_ports()
        channels = [x for x in channels if x not in self.mapping.index.tolist()]
        for port in channels:
            self.mapping.loc[port, 'name'] = ""
            self.mapping.loc[port, 'DI'] = False
            self.add_row(port, "", False)

    def add_row(self, port, name, di):
        assert len(self.port_labels) == len(self.name_inputs) == len(self.di_select)
        cur_len = self.body_layout.rowCount()

        port_label = QLabel(port)
        port_label.setStyleSheet(f"font-family: 'Courier New', monospace; color: {styles.TEXT_SECONDARY}; font-size: 16px;")
        self.port_labels.append(port_label)

        name_input = QLineEdit()
        name_input.setText(name)
        name_input.setPlaceholderText("assign a name…")
        name_input.editingFinished.connect(self.update_var_name)
        self.name_inputs.append(name_input)

        di_select = QCheckBox()
        di_select.setChecked(di)
        di_select.setToolTip("Mark as digital input")
        di_select.stateChanged.connect(self.update_di)
        self.di_select.append(di_select)

        del_btn = QPushButton("✕")
        del_btn.setFixedWidth(28)
        del_btn.setToolTip("Remove this mapping")
        del_btn.setStyleSheet(f"""
            QPushButton {{ color: {styles.DANGER}; border-color: transparent; background: transparent; font-size: 18px; }}
            QPushButton:hover {{ color: white; background: {styles.DANGER}; border-radius: 3px; }}
        """)
        del_btn.clicked.connect(self.del_map)
        self.del_btns.append(del_btn)

        self.body_layout.addWidget(port_label, cur_len, 0)
        self.body_layout.addWidget(name_input, cur_len, 1)
        self.body_layout.addWidget(di_select, cur_len, 2)
        self.body_layout.addWidget(del_btn, cur_len, 3)

    def update_di(self):
        line = self.di_select.index(self.sender())
        self.mapping.iloc[line, self.mapping.columns.get_loc('DI')] = self.di_select[line].isChecked()

    def update_var_name(self):
        line = self.name_inputs.index(self.sender())
        self.mapping.iloc[line, self.mapping.columns.get_loc('name')] = self.name_inputs[line].text()

    def save(self):
        self.mapping.to_csv(self.map_file)

    def create(self):
        dialog = NewSetupDialog()
        dialog.exec_()

        if dialog.fname is not None:
            setup_path = os.path.join(self.root_dir, dialog.fname)
            os.mkdir(setup_path)
            starter_code = f"\nfrom pyBehavior.gui import *\n\nclass {dialog.fname}(SetupGUI):\n    def __init__(self):\n        super({dialog.fname}, self).__init__(Path(__file__).parent.resolve())\n"
            if dialog.use_ni_cards.isChecked():
                new_map_file = os.path.join(setup_path, 'port_map.csv')
                channels = self.scan_ports()
                pd.DataFrame({"port": channels, "name": [""] * len(channels), "DI": [False] * len(channels)}).set_index("port").to_csv(new_map_file)
                starter_code = "from pyBehavior.interfaces.ni import *\n" + starter_code
            if dialog.use_rpi.isChecked():
                if dialog.is_rpi_remote.isChecked():
                    with open(os.path.join(setup_path, 'rpi_config.yaml'), 'w') as f:
                        f.write(f"HOST: {dialog.rpi_host.text()}\nPORT: {dialog.rpi_port.text()}\nUSER: {dialog.rpi_user.text()}")
                    starter_code = "from pyBehavior.interfaces.rpi.remote import *\n" + starter_code
                else:
                    with open(os.path.join(setup_path, 'rpi_config.yaml'), 'w') as f:
                        f.write("LOCAL: true")
                    starter_code = "from pyBehavior.interfaces.rpi.local import *\n" + starter_code
            os.mkdir(os.path.join(setup_path, 'protocols'))
            with open(os.path.join(setup_path, 'gui.py'), 'w') as f:
                f.write(starter_code)
            if dialog.use_ni_cards.isChecked():
                self.map_file_select.addItems([dialog.fname])
                self.map_file_select.setCurrentText(dialog.fname)

    def change_map_file(self):
        for i in range(len(self.port_labels)):
            self.port_labels[i].deleteLater()
            self.name_inputs[i].deleteLater()
            self.di_select[i].deleteLater()
            self.del_btns[i].deleteLater()
        self.port_labels = []
        self.name_inputs = []
        self.di_select = []
        self.del_btns = []
        self.load_map()
        self.fill_body()

    def del_map(self):
        line = self.del_btns.index(self.sender())
        port = self.port_labels[line].text()
        for attr in ('port_labels', 'name_inputs', 'di_select', 'del_btns'):
            lst = getattr(self, attr)
            lst[line].deleteLater()
            del lst[line]
        self.mapping.drop(index=port, inplace=True)


class SetupSelectDialog(QDialog):
    def __init__(self, root_dir):
        super(SetupSelectDialog, self).__init__()
        self.setWindowTitle("Select Setup")
        setups = [x.name for x in Path(root_dir).iterdir()
                  if x.is_dir() and 'gui.py' in [j.name for j in x.iterdir()]]

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("SELECT SETUP")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {styles.ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {styles.BORDER_SUBTLE};")
        layout.addWidget(sep)

        self.setup_select = QListWidget()
        self.setup_select.addItems(setups)
        self.setup_select.setMinimumHeight(120)
        layout.addWidget(self.setup_select)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        self.setMinimumWidth(300)


class MainWindow(QMainWindow):
    def __init__(self, root_dir):
        super(MainWindow, self).__init__()
        self.root_dir = root_dir
        sys.path.append(root_dir)
        self.setWindowTitle("pyBehavior")
        self.setMinimumWidth(280)

        self.settings_dialog = Settings(self.root_dir)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Branding
        brand = QLabel("pyBehavior")
        brand.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {styles.ACCENT};
            letter-spacing: 2px;
            padding-bottom: 4px;
        """)
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)

        sub = QLabel("Behavioral Protocol Control System")
        sub.setStyleSheet(f"color: {styles.TEXT_SECONDARY}; font-size: 16px; letter-spacing: 0.5px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {styles.BORDER_SUBTLE}; margin: 6px 0;")
        layout.addWidget(sep)

        self.settings_btn = QPushButton("Edit Port Mappings")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        layout.addWidget(self.settings_btn)

        self.setup_btn = QPushButton("Open Setup GUI")
        self.setup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.ACCENT_SOFT};
                color: {styles.ACCENT};
                border: 1px solid {styles.ACCENT};
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
            }}
            QPushButton:hover {{ background-color: {styles.ACCENT_DIM}; color: {styles.BG_DEEP}; }}
        """)
        self.setup_btn.clicked.connect(self.open_setup_dialog)
        layout.addWidget(self.setup_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_settings_dialog(self):
        self.settings_dialog.show()

    def open_setup_dialog(self):
        dialog = SetupSelectDialog(self.root_dir)
        res = dialog.exec_()
        if res:
            setup = dialog.setup_select.currentItem().text()
            import importlib
            setup_mod = importlib.import_module(f'{setup}.gui')
            self.setup_GUI = getattr(setup_mod, setup)()
            self.setup_GUI.show()


def main():
    app = QApplication([])
    styles.apply(app)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root_dir', default=None)
    args = parser.parse_args()

    if args.root_dir is None:
        try:
            with open(os.path.expanduser(os.path.join('~', '.pyBehavior_path')), 'r') as f:
                path = os.path.expanduser(f.readline().strip())
        except Exception:
            raise ValueError('No root_dir provided and no default path at ~/.pyBehavior_path')
    else:
        path = args.root_dir

    assert os.path.exists(path), f"root_dir '{path}' does not exist"
    window = MainWindow(path)
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
