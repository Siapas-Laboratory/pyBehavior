import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QComboBox, QFileDialog, QFrame, QLineEdit)
from pathlib import Path
from datetime import datetime
import importlib
import yaml
import os
from ratBerryPi.client import Client
from abc import ABCMeta, abstractmethod
from collections import UserDict
from pyBehavior.protocols import *
import logging
import paramiko
from scp import SCPClient
import typing

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
                self.rpi_config = yaml.safe_load(f)
            self.client = Client(self.rpi_config['HOST'], 
                                 self.rpi_config['PORT'])
            self.client.new_channel("run")
            self.has_rpi = True
        else:
            self.has_rpi = False

        container = QWidget()
        self.layout = QVBoxLayout()
        menu_layout = QHBoxLayout()

        # load all protocols into the dropdown menu
        protocols = [ i.stem for i in (self.loc/'protocols').iterdir() if i.is_file() and i.name[-3:] == '.py' ]
        self._prot_select = QComboBox()
        self._prot_select.addItems([""] + protocols)
        self._prot_select.currentIndexChanged.connect(self._change_protocol)

        # create a start button for starting a protocol
        self._start_btn = QPushButton("start")
        self._start_btn.setCheckable(True)
        self._start_btn.setEnabled(False)
        self.running = False
        self._start_btn.clicked.connect(self._start_protocol)

        # stop button for stopping a protocol
        self._stop_btn = QPushButton("stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_protocol)

        # add elements to the layout
        menu_layout.addWidget(self._prot_select)
        menu_layout.addWidget(self._start_btn)
        menu_layout.addWidget(self._stop_btn)
        self.layout.addLayout(menu_layout)
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # initialize the state machine as none
        # until a protocol is selected
        self.state_machine = None

        # placeholder attributes for
        # the collection of reward modules
        self.reward_modules = ModuleDict()

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # placeholder for file handler
        self._log_fh = None

        # create handler for logging to the console
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter and add it to the handler
        self._formatter = logging.Formatter('%(asctime)s.%(msecs)03d, %(levelname)s, %(message)s',
                                           "%Y-%m-%d %H:%M:%S")
        ch.setFormatter(self._formatter)
        # add the handlers to the logger
        self.logger.addHandler(ch)

        self.eventstring_handlers = {}

    def _start_protocol(self):
        # dialog to select a save directory
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        dir_name = os.path.join(dir_name, 
                                datetime.strftime(datetime.now(), f"{self._prot_select.currentText()}_%Y_%m_%d_%H_%M_%S"))
        os.makedirs(dir_name)
        self._filename = Path(dir_name)/datetime.strftime(datetime.now(), f"{self._prot_select.currentText()}_%Y_%m_%d_%H_%M_%S.log")

        # replace file handler
        self._log_fh = logging.FileHandler(self._filename)
        self._log_fh.setLevel(logging.DEBUG)
        self._log_fh.setFormatter(self._formatter)
        self.logger.addHandler(self._log_fh)

        # create the state machine
        prot = ".".join([self.loc.name, "protocols", self.prot_name])
        setup_mod = importlib.import_module(prot)
        state_machine = getattr(setup_mod, self.prot_name)
        if not issubclass(state_machine, Protocol):
            raise ValueError("protocols must be subclasses of utils.protocols.Protocol")
        self.state_machine = state_machine(self)
        if self.has_rpi: self.client.run_command('record', channel = 'run')

        # update gui element accessibility
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._prot_select.setEnabled(False)

        # raise flag saying that we're running
        self.running = True

    def _stop_protocol(self):

        self.running = False
        if self.has_rpi: 
            rpi_data_path = self.client.get('data_path')
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(self.client.host, username = self.rpi_config['USER'], look_for_keys = True)
            scp_client = SCPClient(ssh_client.get_transport())
            scp_client.get(rpi_data_path, self._filename.parent.as_posix())
            self.logger.info(f"rpi logs saved at: {self.client.get('data_path')}")
            self.client.run_command('stop_recording', channel = 'run')
        # remove file handler
        self.logger.removeHandler(self._log_fh)
        
        # update gui elements
        self._start_btn.setEnabled(True)
        self._start_btn.toggle()
        self._prot_select.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def _change_protocol(self):
        # import and create the statemachine
        self.prot_name = self._prot_select.currentText()
        if len(self.prot_name)>0:
            self._start_btn.setEnabled(True)
        else:
            self.state_machine = None
            self._start_btn.setEnabled(False)
    
    def _template_state_machine_input_handler(self, data, formatter:typing.Callable, before:typing.Callable, event_line:str):
        if before is not None:
            before(data)
        if self.running:
            curr_state = self.state_machine.current_state.id
            self.state_machine.handle_input(formatter(data))
            if self.state_machine.current_state.id != curr_state:
                self.log(f"entered state {self.state_machine.current_state.id}", event_line)

    def trigger_reward(self, module:str, amount:float, **kwargs):
        """
        trigger reward on a specified module

        Args:
            module: str
                module to deliver the reward to
            amount: float
                amount of reward in mL
        """

        self.log(f"triggering {amount:.2f} mL reward on module {module}")
        self.reward_modules[module].trigger_reward(amount, **kwargs)

    def log(self, event:str, event_line:str = None):
        """
        log events. optionally simmultaneously
        send an event string using an EventstringSender
        NOTE: currently EventstringSender is only configured
        to toggle digital lines on a national instruments card

        Args:
            event: str
                event to log
            event_line: str (optional)
                name of the event line to use to log
        """

        if event_line:
            self.eventstring_handlers[event_line].send(event)
        else:
            self.logger.info(event)

    def init_NIDIDaemon(self, channels:dict, fs:float = 1000, start:bool = False):
        """
        start a daemon to monitor digital input lines on a
        national instruments card

        Args:
            channels: dict
                dictionary with keys being human readable
                names for digital inputs and values being the
                associated address of the digital line
            fs: float (optional)
                sampling rate for polling the digital lines
                in Hz [default: 1000]
            start: bool
                whether or not to start the daemon
                [default: True]
                
        """
        
        from pyBehavior.interfaces.ni import NIDIDaemon
        self.di_daemon = NIDIDaemon(fs)
        for i, v in channels.items():
            self.di_daemon.register(v, i)
        self.di_daemon_thread = QThread()
        self.di_daemon.moveToThread(self.di_daemon_thread)
        self.di_daemon_thread.started.connect(self.di_daemon.run)
        self.di_daemon.finished.connect(self.di_daemon_thread.quit)
        if start:
            self.di_daemon_thread.start()
        return self.di_daemon, self.di_daemon_thread
    
    def register_state_machine_input(self, signal:pyqtSignal, input_type:str, metadata = None, 
                                     before:typing.Callable = None, event_line:str = None):
        """
        register a pyqtsiganl as an input to the state machine
        running a protocol

        Args:
            signal: pyqtSignal
                signal to register
            input_type: str
                identifier for the type of input
                this signal represents
            metadata:
                additional metadata to attach to the input
                data sent to the state machine
            before: typing.Callable
                function to call before feeding the input to the state machine
                this function should take as input the data associated with the signal
            event_line: str
                event line to use to log state machine transitions
        """

        formatter = lambda x: {"type": input_type, "data": x, "metadata": metadata}
        signal.connect(lambda x: self._template_state_machine_input_handler(x, formatter, before, event_line))

    def add_eventstring_handler(self, event_line_name:str, event_line_port:str):
        """
        add a new eventstring handler. 

        Args:
            event_line_name: str
                name to assign to event line
            event_line_port: str
                address of the digital line to toggle when
                raising this event line
        """

        from pyBehavior.interfaces.ni import EventstringSender
        self.eventstring_handlers[event_line_name] = EventstringSender(self, event_line_name, event_line_port)
        return self.eventstring_handlers[event_line_name] 

    def closeEvent(self, event):
        if self.running: self._stop_protocol()
        if hasattr(self, 'di_daemon'):
            if self.di_daemon.running:
                self.di_daemon.stop()
                self.di_daemon_thread.quit()
        event.accept()


class RewardWidgetMeta(type(QFrame), ABCMeta):
    pass

class RewardWidget(QFrame, metaclass = RewardWidgetMeta):
    """
    abstract class to be inherited when creating widgets for reward control
    defines an abstract method trigger_reward which must be defined in the subclass
    """
    @abstractmethod
    def trigger_reward(amount):
        ...

class ModuleDict(UserDict):
    def __setitem__(self, key, value):
        if issubclass(type(value), RewardWidget):
            super().__setitem__(key, value)
        else:
            raise ValueError("entries in ModuleDict must be instances of subclasses of gui.RewardWidget")
    
class LoggableLineEdit(QLineEdit):

    def __init__(self, logger, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.name = name
        self.textChanged.connect(self.log_change)

    def log_change(self, text):
        self.logger.info(f"{self.name} updated to {self.text()}")