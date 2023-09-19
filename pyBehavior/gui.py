import pandas as pd
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QFileDialog
from pathlib import Path
from datetime import datetime
import importlib
import yaml
import os
from ratBerryPi.client import Client
from abc import ABCMeta, abstractmethod
from collections import UserDict
from pyBehavior.protocols import *

class SetupGUI(QMainWindow):
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
        super(SetupGUI, self).__init__()
        self.loc = Path(loc)

        # if there is a ni port map for this setup load it
        if os.path.exists(self.loc/'port_map.csv'):
            mapping = pd.read_csv(self.loc/'port_map.csv')
            self.mapping = mapping.set_index('name')['port'].fillna("")
        else:
            self.mapping = None

        # if there is a config file for connecting to a raspberry pi load it
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

        # load all protocols into the dropdown menu
        protocols = [ i.stem for i in (self.loc/'protocols').iterdir() if i.is_file() and i.name[-3:] == '.py' ]
        self.prot_select = QComboBox()
        self.prot_select.addItems([""] + protocols)
        self.prot_select.currentIndexChanged.connect(self.change_protocol)

        # create a start button for starting a protocol
        self.start_btn = QPushButton("start")
        self.start_btn.setCheckable(True)
        self.start_btn.setEnabled(False)
        self.running = False
        self.start_btn.clicked.connect(self.start_protocol)

        # stop button for stopping a protocol
        self.stop_btn = QPushButton("stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_protocol)

        # add elements to the layout
        self.menu_layout.addWidget(self.prot_select)
        self.menu_layout.addWidget(self.start_btn)
        self.menu_layout.addWidget(self.stop_btn)
        self.layout.addLayout(self.menu_layout)
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # initialize the state machine as none
        # until a protocol is selected
        self.state_machine = None

        # create a timer to periodically save results
        # when the protocol is running
        self.timer = QTimer()
        self.timer.timeout.connect(self.save)

        # placeholder attributes for the save buffer and 
        # the collection of reward modules
        self.buffer = {}
        self.reward_modules = ModuleDict()

    def start_protocol(self):
        self.buffer = {} # clear the save buffer
        # dialog to select a save directory
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        self.filename = Path(dir_name)/datetime.strftime(datetime.now(), f"{self.prot_select.currentText()}_%Y_%m_%d_%H_%M_%S.csv")
        # create the state machine
        prot = ".".join([self.loc.name, "protocols", self.prot_name])
        setup_mod = importlib.import_module(prot)
        state_machine = getattr(setup_mod, self.prot_name)
        if not issubclass(state_machine, Protocol):
            raise ValueError("protocols must be subclasses of utils.protocols.Protocol")
        self.state_machine = state_machine(self)
        # start the timer for saving
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
        buff = pd.Series(self.buffer, dtype = str).rename('event').to_frame()
        if self.filename.exists():
            data = pd.read_csv(self.filename, index_col = 0)
            data = pd.concat(( data, buff), axis=0)
        else:
             data = buff
        data.to_csv(self.filename)
        self.buffer = {}


class RewardWidgetMeta(type(QWidget), ABCMeta):
    pass

class RewardWidget(QWidget, metaclass = RewardWidgetMeta):
    """
    abstract class to be inherited when creating widgets for reward control
    defines an abstract method trigger_reward which must be defined in the subclass
    """
    @abstractmethod
    def trigger_reward(amount, small = False):
        ...

class ModuleDict(UserDict):
    def __setitem__(self, key, value):
        if issubclass(type(value), RewardWidget):
            super().__setitem__(key, value)
        else:
            raise ValueError("entries in ModuleDict must be instances of subclasses of utils.gui.RewardWidget")
    