import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QComboBox, QFileDialog, QFrame, QLineEdit)
from pathlib import Path
from datetime import datetime
import importlib
import yaml
import os
from ratBerryPi.remote.client import Client
from abc import ABCMeta, abstractmethod
from collections import UserDict
from pyBehavior.protocols import *
import logging
import paramiko
from scp import SCPClient
import typing


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
    """
    custom dictionary with checking to enforce
    all values are instances of a subclass of RewardWidget
    by extension this enforces that all values in this dictionary have
    trigger_reward methods enabling the use of trigger_reward
    method in SetupGUI below
    """
    def __setitem__(self, key, value):
        if issubclass(type(value), RewardWidget):
            super().__setitem__(key, value)
        else:
            raise ValueError("entries in ModuleDict must be instances of subclasses of gui.RewardWidget")
    

class SetupGUI(QMainWindow):
    """
    base class for all setup visualizers
    includes a dropdown menu at the top of the window for selecting a protocol
    as well as a start and stop button. upon selecting a protocol an instance of
    the corresponding statemachine will be created. pressing the start button opens
    a filedialog to select a folder to save any timestamps to. all timestamping 
    is handled through the log function. 

    Attributes:
        loc (Path):
            path to the directory with gui and protocol code for this setup
        mapping (pd.Series):
            pandas series mapping names to nidaqmx ports. keys are human
            readable names and values are the port addresses. this mapping
            is read from a file called port_map.csv which should be in
            the setup directory 
        rpi_config (dict):
            dictionary representing the contents of the rpi_config.yaml file
            which should be stored in the setup directory. the file itself 
            should contain the fields USER, HOST, and PORT which specify the 
            username for logging into the pi, the hostname for the pi, and the 
            port number that the ratBerryPi server is serving on
        client (ratBerryPi.Client)
            client for communicating with a remote ratBerryPi server
        layout (PyQt5.QtWidgets.QVBoxLayout)
            vertical box layout for constructing the GUI. any additional gui elements
            should be added to this layout to be displayed
        reward_modules (ModuleDict)
            dictionary mapping names to instances of RewardWidgets
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
            self._has_rpi = True
        else:
            self._has_rpi = False

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
        self._running = False
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
        self._state_machine = None

        # placeholder attributes for
        # the collection of reward modules
        self.reward_modules = ModuleDict()

        self._logger = logging.getLogger()
        self._logger.setLevel(logging.DEBUG)

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
        self._logger.addHandler(ch)

        self._eventstring_handlers = {}

        self._di_daemon = None
        self._di_daemon_thread = None

    @property
    def ni_di(self) -> pd.DataFrame:
        """
        dataframe storing references to pyqt signals
        emited on a given edge of a digital signal. 
        each row correponds to a digital line on an NI card
        and is addressed by the name assigned when calling 
        self.init_NIDIDaemon. the rising_edge column contains 
        signals emitted on the rising edge of the line.
        similarly the falling edge column contains signals emited on
        the falling edge of the line
        """
        return self._di_daemon.channels
    
    def init_NIDIDaemon(self, channels: typing.Dict[str, str], fs = 1000, start = False):
        """
        initialize a daemon that will poll a set of digital input lines
        through nidaqmx continuously in the background and emit signals
        on the rising and falling edges of each line

        Args:
            channels:
                dictionary or pandas series mapping names to 
                addresses for digital input lines to monitor.
                keys should be names and values should be addresses
            fs:
                rate at which to poll the digital input lines in Hz.
            start:
                flag indicating whether or not to automatically
                start the daemon
        """

        from pyBehavior.interfaces.ni import NIDIDaemon
        self._di_daemon = NIDIDaemon(fs)
        for i, v in channels.items():
            self._di_daemon.register(v, i)
        self._di_daemon_thread = QThread()
        self._di_daemon.moveToThread(self._di_daemon_thread)
        self._di_daemon_thread.started.connect(self._di_daemon.run)
        self._di_daemon.finished.connect(self._di_daemon_thread.quit)
        if start: self._di_daemon_thread.start()

    def start_NIDIDaemon(self):
        """
        start the thread running the NI DI Daemon
        """
        assert self._di_daemon_thread is not None, "must initialize the daemon first"
        self._di_daemon_thread.start()

    @property
    def prot_name(self) -> str:
        """
        name of the currently selected protocol
        """
        return self._prot_select.currentText()
    
    
    def _start_protocol(self) -> None:
        """
        initialize the state machine for the currently selected
        protocol and create a new log file
        """

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
        self._logger.addHandler(self._log_fh)

        # create the state machine
        prot = ".".join([self.loc.name, "protocols", self.prot_name])
        setup_mod = importlib.import_module(prot)
        state_machine = getattr(setup_mod, self.prot_name)
        if not issubclass(state_machine, Protocol):
            raise ValueError("protocols must be subclasses of utils.protocols.Protocol")
        self._state_machine = state_machine(self)
        if self._has_rpi: self.client.run_command('record', channel = 'run')

        # update gui element accessibility
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._prot_select.setEnabled(False)
        self.log("starting protocol")
        # raise flag saying that we're running
        self._running = True

    def _stop_protocol(self):
        """
        stop logging to the current log file and copy 
        any data from a remote ratBerryPi to the log directory
        """
        self.log("stopping protocol")
        self._running = False
        if self._has_rpi: 
            rpi_data_path = self.client.get('data_path')
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(self.client.host, username = self.rpi_config['USER'], look_for_keys = True)
            scp_client = SCPClient(ssh_client.get_transport())
            scp_client.get(rpi_data_path, self._filename.parent.as_posix())
            self._logger.info(f"rpi logs saved at: {self.client.get('data_path')}")
            self.client.run_command('stop_recording', channel = 'run')
        # remove file handler
        self._logger.removeHandler(self._log_fh)
        
        # update gui elements
        self._start_btn.setEnabled(True)
        self._start_btn.toggle()
        self._prot_select.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def _change_protocol(self) -> None:
        """
        callback for switching between protocols
        """

        if len(self.prot_name)>0:
            self._start_btn.setEnabled(True)
        else:
            self._state_machine = None
            self._start_btn.setEnabled(False)
    
    def _template_state_machine_input_handler(self, data, formatter:typing.Callable, before:typing.Callable, event_line:str):
        if before is not None:
            before(data)
        if self._running:
            curr_state = self._state_machine.current_state.id
            self._state_machine.handle_input(formatter(data))
            if self._state_machine.current_state.id != curr_state:
                self.log(f"STATE MACHINE ENTERED STATE: {self._state_machine.current_state.id}", event_line)

    def trigger_reward(self, module:str, amount:float, event_line:str = None, **kwargs):
        """
        trigger reward on a specified module

        Args:
            module: str
                module to deliver the reward to
            amount: float
                amount of reward in mL
        """

        self.log(f"triggering {amount:.2f} mL reward on module {module}", event_line=event_line)
        self.reward_modules[module].trigger_reward(amount, **kwargs)

    def log(self, event:str, event_line:str = None, raise_event_line:bool = True):
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
            self._eventstring_handlers[event_line].send(event)
        elif raise_event_line:
            if len(self._eventstring_handlers)>0:
                event_line = list(self._eventstring_handlers.keys())[0]
                self._eventstring_handlers[event_line].send(event)
        else:
            self._logger.info(event)

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
        self._di_daemon = NIDIDaemon(fs)
        for i, v in channels.items():
            self._di_daemon.register(v, i)
        self._di_daemon_thread = QThread()
        self._di_daemon.moveToThread(self._di_daemon_thread)
        self._di_daemon_thread.started.connect(self._di_daemon.run)
        self._di_daemon.finished.connect(self._di_daemon_thread.quit)
        if start:
            self._di_daemon_thread.start()
    
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
        self._eventstring_handlers[event_line_name] = EventstringSender(self, event_line_name, event_line_port)
        return self._eventstring_handlers[event_line_name] 

    def closeEvent(self, event):
        if self._running: self._stop_protocol()
        if hasattr(self, 'di_daemon'):
            if self._di_daemon.running:
                self._di_daemon.stop()
                self._di_daemon_thread.quit()
        event.accept()

    
class LoggableLineEdit(QLineEdit):

    def __init__(self, name, gui:SetupGUI, event_line:str = None, raise_event_line:bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gui = gui
        self.name = name
        self.event_line = event_line
        self.raise_event_line = raise_event_line
        self.editingFinished.connect(self.log_change)

    def log_change(self):

        self.gui.log(f"{self.name} updated to {self.text()}", event_line=self.event_line, raise_event_line=self.raise_event_line)
