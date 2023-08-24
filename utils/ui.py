import numpy as np
import pandas as pd
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QSpinBox, QFileDialog
from PyQt5.QtGui import  QDoubleValidator
from pathlib import Path
import time
from datetime import datetime
import importlib
import yaml
import os
from utils.rpi import path_to_rpi_reward_mod
import sys
sys.path.append(path_to_rpi_reward_mod)
from client import Client


class SetupVis(QMainWindow):
    """
    base class for all setup visualizers
    includes a dropdown menu at the top of the window for selecting a protocol
    as well as a start and stop button. upon selecting a protocol an instance of
    the corresponding statemachine will be created. pressing the start button opens
    a filedialog to select a folder to save any timestamps to. all timestamping 
    is handled through the log function which writes the timestamp to a buffer which is
    periodically saved to a csv file in the save directory if the protocol is running

    """
    def __init__(self, loc):
        super(SetupVis, self).__init__()
        self.loc = Path(loc)
        if os.path.exists(self.loc/'port_map.csv'):
            mapping = pd.read_csv(self.loc/'port_map.csv')
            self.mapping = mapping.set_index('name')['port'].fillna("")
        else:
            self.mapping = None
        if os.path.exists(self.loc/'rpi_config.yaml'):
            with open(self.loc/'rpi_config.yaml', 'r') as f:
                rpi_config = yaml.safe_load(f)
            self.client = Client(rpi_config['HOST'], 
                                 rpi_config['PORT'], 
                                 rpi_config['BROADCAST_PORT'])
            self.client.connect()

        container = QWidget()
        self.layout = QVBoxLayout()
        self.menu_layout = QHBoxLayout()

        protocols = [ i.stem for i in (self.loc/'protocols').iterdir() ]
        self.prot_select = QComboBox()
        self.prot_select.addItems([""] + protocols)
        self.prot_select.currentIndexChanged.connect(self.change_protocol)

        self.start_btn = QPushButton("start")
        self.start_btn.setCheckable(True)
        self.start_btn.setEnabled(False)
        self.running = False
        self.start_btn.clicked.connect(self.start_protocol)

        self.stop_btn = QPushButton("stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_protocol)

        self.menu_layout.addWidget(self.prot_select)
        self.menu_layout.addWidget(self.start_btn)
        self.menu_layout.addWidget(self.stop_btn)
        self.layout.addLayout(self.menu_layout)

        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.state_machine = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.save)
        self.buffer = {}
        self.reward_modules = {}

    def start_protocol(self):
        self.buffer = {}
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        self.filename = Path(dir_name)/datetime.strftime(datetime.now(), f"{self.prot_select.currentText()}_%Y_%m_%d_%H_%M_%S.csv")
        prot = (Path("setups")/self.loc.name/'protocols'/self.prot_name).as_posix()
        setup_mod = importlib.import_module(prot.replace('/','.'))
        state_machine = getattr(setup_mod, self.prot_name)
        self.state_machine = state_machine(self)
        self.timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.running = True
        self.prot_select.setEnabled(False)

    def stop_protocol(self):
        self.running = False
        self.timer.stop()
        self.save()
        self.start_btn.setEnabled(True)
        self.start_btn.toggle()
        self.prot_select.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def change_protocol(self):
        # import and create the statemachine
        self.prot_name = self.prot_select.currentText()
        if len(self.prot_name)>0:
            self.start_btn.setEnabled(True)
        else:
            self.state_machine = None
            self.start_btn.setEnabled(False)
    
    def trigger_reward(self, module, small):
        self.reward_modules[module].trigger_reward(small)

    def log(self, event):
        self.buffer.update({datetime.now(): event})

    def save(self):
        buff = pd.Series(self.buffer).rename('event').to_frame()
        if self.filename.exists():
            data = pd.read_csv(self.filename, index_col = 0)
            data = pd.concat(( data, buff), axis=0)
        else:
             data = buff
        data.to_csv(self.filename)
        self.buffer = {}