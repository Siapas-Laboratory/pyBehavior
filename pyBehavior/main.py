import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QDialog, QListWidget, QDialogButtonBox,
                             QHBoxLayout,QComboBox, QLineEdit, QLabel,  QScrollArea, 
                             QGridLayout, QCheckBox, QInputDialog)
from pathlib import Path
import numpy as np
import pandas as pd
from pathlib import Path
import nidaqmx
import os


class NewSetupDialog(QDialog):
    def __init__(self):
        super(NewSetupDialog, self).__init__()

        self.fname = None
        buttonBox = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.check_input)
        cancel.clicked.connect(self.reject)
        buttonBox.addWidget(ok)
        buttonBox.addWidget(cancel)

        layout = QVBoxLayout()
        self.fname_input = QLineEdit()
        message = QLabel("Please enter a name for the new setup. Avoid spaces and all symbols except for _")
        self.use_ni_cards = QCheckBox("Check here if this setup will use National Instruments Cards")
        self.use_rpi = QCheckBox("Check here if this setup will connect remotely to a ratBerryPi")
        rpi_dialog_layout = QVBoxLayout()

        host_layout = QHBoxLayout()
        host_label = QLabel('HOST')
        self.rpi_host = QLineEdit()
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.rpi_host)
        rpi_dialog_layout.addLayout(host_layout)

        port_layout = QHBoxLayout()
        port_label = QLabel('PORT')
        self.rpi_port = QLineEdit()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.rpi_port)
        rpi_dialog_layout.addLayout(port_layout)

        user_layout = QHBoxLayout()
        user_label = QLabel('USER')
        self.rpi_user = QLineEdit()
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.rpi_user)
        rpi_dialog_layout.addLayout(user_layout)

        self.rpi_dialog = QWidget()
        self.rpi_dialog.setLayout(rpi_dialog_layout)
        self.rpi_dialog.hide()

        self.use_rpi.clicked.connect(self.show_rpi_dialog)

        layout.addWidget(message)
        layout.addWidget(self.fname_input)
        layout.addWidget(self.use_ni_cards)
        layout.addWidget(self.use_rpi)
        layout.addWidget(self.rpi_dialog)
        layout.addLayout(buttonBox)
        self.setLayout(layout)
        self.orig_size = self.minimumSizeHint()
        self.height =self.orig_size.height()
        self.width =self.orig_size.width()


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
        valid = (len(self.fname)>1) & np.all([x.isalnum() or (x == "_") for x in self.fname])
        if valid:
            self.accept()


class Settings(QMainWindow):
    def __init__(self, setup_dir):
        super(Settings, self).__init__()
        self.setup_dir = setup_dir

        # create layout elements
        self.layout = QVBoxLayout()
        self.header_layout = QHBoxLayout()

        # create a drop down menu of available mappings
        available_mappings = []
        for i in Path(setup_dir).iterdir():
            if i.is_dir():
                if 'port_map.csv' in [j.name for j in i.iterdir()]:
                    available_mappings.append(i.stem)
            
        self.map_file_select = QComboBox()
        self.map_file_select.addItems(available_mappings)
        if len(available_mappings)>0:
            self.map_file = os.path.join(setup_dir,self.map_file_select.currentText(),'port_map.csv')
            self.mapping = pd.read_csv(self.map_file)
            self.mapping = self.mapping.set_index('port')['name'].fillna("")
        else:
            self.map_file = None
            self.mapping = pd.DataFrame()

        self.map_file_select.currentIndexChanged.connect(self.change_map_file)
        self.header_layout.addWidget(self.map_file_select)
        
        # button to create new map file
        self.create_btn = QPushButton("create")
        self.create_btn.clicked.connect(self.create)
        self.header_layout.addWidget(self.create_btn)

        # button to save current mappings to selected map file
        self.save_btn = QPushButton("save")
        self.save_btn.clicked.connect(self.save)
        self.header_layout.addWidget(self.save_btn)
        self.layout.addLayout(self.header_layout)

        # fill the body of the window with port labels and inputs for names to assign
        self.body_layout = QGridLayout()
        self.fill_body()
        self.body_widget = QWidget()       
        self.body_widget.setLayout(self.body_layout)
        
        # make it scrollable
        self.scroll = QScrollArea() 
        self.scroll.setWidget(self.body_widget)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)

        #add the widget
        self.layout.addWidget(self.scroll)
        self.add_btn = QPushButton('Add')
        self.add_btn.clicked.connect(self.add_map)
        self.layout.addWidget(self.add_btn)
        self.get_btn = QPushButton('Get All Ports')
        self.get_btn.clicked.connect(self.get_all_ports)
        self.layout.addWidget(self.get_btn)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def add_map(self):
        port, ok = QInputDialog().getText(self, "New Mapping", "Enter name of the new port to map:")
        if ok:

            self.mapping.loc[port] = ""

            port_label = QLabel()
            port_label.setText(port)
            self.port_labels.append(port_label)

            name_input = QLineEdit()
            name_input.setText(self.mapping.loc[port])
            name_input.editingFinished.connect(self.update_var_name)
            self.name_inputs.append(name_input)

            del_btn = QPushButton("del")
            del_btn.clicked.connect(self.del_map)
            self.del_btns.append(del_btn)

            cur_len = self.body_layout.rowCount()
            self.body_layout.addWidget(port_label, cur_len, 0)
            self.body_layout.addWidget(name_input, cur_len, 1)
            self.body_layout.addWidget(del_btn, cur_len, 2)

            self.mapping.loc[port] = ""

    def fill_body(self):
        """
        fill the body of the window with label 
        and line edit widgets for all mappings
        """
        self.port_labels = []
        self.name_inputs = []
        self.del_btns = []
        for i,(port, name) in enumerate(self.mapping.items()):

            port_label = QLabel()
            port_label.setText(port)
            self.port_labels.append(port_label)

            name_input = QLineEdit()
            name_input.setText(name)
            name_input.editingFinished.connect(self.update_var_name)
            self.name_inputs.append(name_input)


            del_btn = QPushButton("del")
            del_btn.clicked.connect(self.del_map)
            self.del_btns.append(del_btn)

            self.body_layout.addWidget(port_label, i, 0)
            self.body_layout.addWidget(name_input, i, 1)
            self.body_layout.addWidget(del_btn, i, 2)

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
        else:
            return []

    def get_all_ports(self):
        channels = self.scan_ports()
        channels = list(filter(lambda x: x not in self.mapping.index.tolist(), channels))
        cur_len = self.body_layout.rowCount()
        for i, port in enumerate(channels, cur_len):

            self.mapping.loc[port] = ""

            port_label = QLabel()
            port_label.setText(port)
            self.port_labels.append(port_label)

            name_input = QLineEdit()
            name_input.setText(self.mapping.loc[port])
            name_input.editingFinished.connect(self.update_var_name)
            self.name_inputs.append(name_input)


            del_btn = QPushButton("del")
            del_btn.clicked.connect(self.del_map)
            self.del_btns.append(del_btn)

            self.body_layout.addWidget(port_label, i, 0)
            self.body_layout.addWidget(name_input, i, 1)
            self.body_layout.addWidget(del_btn, i, 2)

    def update_var_name(self):
        line = self.name_inputs.index(self.sender())
        self.mapping.iloc[line] = self.name_inputs[line].text()

    def save(self):
        self.mapping.to_frame().to_csv(self.map_file)
    
    def create(self):
        dialog = NewSetupDialog()
        dialog.exec_()

        if dialog.fname is not None:
            setup_path = os.path.join(self.setup_dir, dialog.fname)
            os.mkdir(setup_path)
            starter_code = f"""
from pyBehavior.gui import *

class {dialog.fname}(SetupGUI):
    def __init__(self):
        super({dialog.fname}, self).__init__(Path(__file__).parent.resolve())
"""
            if dialog.use_ni_cards.isChecked():
                new_map_file = os.path.join(setup_path, 'port_map.csv')
                channels = self.scan_ports()
                new_mapping = pd.Series([""]* len(channels), dtype = str, index = pd.Index(channels, name = "port")).rename("name")
                new_mapping.to_frame().to_csv(new_map_file)
                starter_code = "from pyBehavior.interfaces.ni import *\n" + starter_code

            if dialog.use_rpi.isChecked():
                with open(os.path.join(setup_path, 'rpi_config.yaml'), 'w') as f:
                    f.write(f"HOST: {dialog.rpi_host.text()}\n")
                    f.write(f"PORT: {dialog.rpi_port.text()}\n")
                    f.write(f"USER: {dialog.rpi_user.text()}")
                starter_code = "from pyBehavior.interfaces.rpi import *\n" + starter_code

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
            self.del_btns[i].deleteLater()

        self.map_file = os.path.join(self.setup_dir, str(self.map_file_select.currentText()), 'port_map.csv')
        self.mapping = pd.read_csv(self.map_file).set_index('port')['name'].fillna("")
        self.fill_body()        

    def del_map(self):

        line = self.del_btns.index(self.sender())
        port = self.port_labels[line].text()
        self.port_labels[line].deleteLater()
        del self.port_labels[line]
        self.name_inputs[line].deleteLater()
        del self.name_inputs[line]
        self.del_btns[line].deleteLater()
        del self.del_btns[line]
        self.mapping.drop(index = port, inplace=True)

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
    parser.add_argument('setup_dir')
    args = parser.parse_args()

    window = MainWindow(args.setup_dir)
    window.show()

    app.exec()