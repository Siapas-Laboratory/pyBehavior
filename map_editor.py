from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog, QScrollArea, QGridLayout, QCheckBox
from PyQt5.QtCore import Qt
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
        self.use_rpi = QCheckBox("Check here if this setup will use a Raspberry Pi")
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

        bport_layout = QHBoxLayout()
        bport_label = QLabel('BROADCAST PORT')
        self.rpi_bport = QLineEdit()
        bport_layout.addWidget(bport_label)
        bport_layout.addWidget(self.rpi_bport)
        rpi_dialog_layout.addLayout(bport_layout)

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
        valid = (len(self.fname)>1) & np.all([x.isalnum() or x in ["-", "_"] for x in self.fname])
        if valid:
            self.accept()


class Settings(QMainWindow):
    def __init__(self):
        super(Settings, self).__init__()

        # create layout elements
        self.layout = QVBoxLayout()
        self.header_layout = QHBoxLayout()

        # create a drop down menu of available mappings
        available_mappings = [i.stem for i in Path('setups').iterdir() if 'port_map.csv' in [j.name for j in i.iterdir()]]
        self.map_file_select = QComboBox()
        self.map_file_select.addItems(available_mappings)
        self.map_file = os.path.join('setups',self.map_file_select.currentText(),'port_map.csv')
        self.mapping = pd.read_csv(self.map_file)
        self.mapping = self.mapping.set_index('port')['name'].fillna("")
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
        self.get_btn = QPushButton('Get All Ports')
        self.get_btn.clicked.connect(self.get_all_ports)
        self.layout.addWidget(self.get_btn)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
    
    def fill_body(self):
        """
        fill the body of the window with label 
        and line edit widgets for all mappings
        """
        self.port_labels = []
        self.name_inputs = []
        self.del_btns = []
        for i,(port, name) in enumerate(self.mapping.iteritems()):

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
        try:
            system = nidaqmx.system.System.local()
            channels = []
            for dev in system.devices:
                channels += [i.name for i in dev.di_lines] + [i.name for i in dev.do_lines] + [i.name for i in dev.ai_physical_chans] + [i.name for i in dev.ao_physical_chans]
            channels = np.unique(channels)
        except nidaqmx._lib.DaqNotFoundError: # for debugging purposes if not running on the machine itself
            channels = pd.read_csv('blank_port_map.csv')['port'].tolist()
        return channels

    def get_all_ports(self):
        channels = pd.Series(self.scan_ports())
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

            self.mapping.loc[port] = ""

    def update_var_name(self):
        line = self.name_inputs.index(self.sender())
        self.mapping.iloc[line] = self.name_inputs[line].text()

    def save(self):
        self.mapping.to_frame().to_csv(self.map_file)
    
    def create(self):
        dialog = NewSetupDialog()
        dialog.exec_()

        if dialog.fname is not None:
            setup_path = os.path.join('setups', dialog.fname)
            os.mkdir(setup_path)

            if dialog.use_ni_cards.isChecked():
                new_map_file = os.path.join(setup_path, 'port_map.csv')
                channels = self.scan_ports()
                new_mapping = pd.Series([""]* len(channels), index = pd.Index(channels, name = "port")).rename("name")
                new_mapping.to_frame().to_csv(new_map_file)

            if dialog.use_rpi.isChecked():
                with open(os.path.join(setup_path, 'rpi_config.yaml'), 'w') as f:
                    f.write(f"HOST: {dialog.rpi_host.text()}\n")
                    f.write(f"PORT: {dialog.rpi_port.text()}\n")
                    f.write(f"BROADCAST_PORT: {dialog.rpi_bport.text()}")

            os.mkdir(os.path.join(setup_path, 'protocols'))
            with open(os.path.join(setup_path, 'visualizer.py'), 'w') as f:
                starter_code = f"""
import sys
sys.path.append("../")
from utils.ui import *

class {dialog.fname}(SetupVis):
    def __init__(self):
        super({dialog.fname}, self).__init__(Path(__file__).parent.resolve())
"""          
                f.write(starter_code)

            if dialog.use_ni_cards.isChecked():
                self.map_file_select.addItems([dialog.fname])
                self.map_file_select.setCurrentText(dialog.fname)


    def change_map_file(self):

        for i in range(len(self.port_labels)):
            self.port_labels[i].deleteLater()
            self.name_inputs[i].deleteLater()
            self.del_btns[i].deleteLater()

        self.map_file = f'setups/{str(self.map_file_select.currentText())}/port_map.csv'
        self.mapping = pd.read_csv(self.map_file).set_index('port')['name'].fillna("")
        self.fill_body()        

    def del_map(self):

        line = self.del_btns.index(self.sender())
        port = self.port_labels[line].text()
        print(port)
        self.port_labels[line].deleteLater()
        del self.port_labels[line]
        self.name_inputs[line].deleteLater()
        del self.name_inputs[line]
        self.del_btns[line].deleteLater()
        del self.del_btns[line]
        self.mapping.drop(index = port, inplace=True)

