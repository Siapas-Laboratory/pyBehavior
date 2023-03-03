import numpy as np
import pandas as pd
from nidaqmx import constants, Task
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QSpinBox, QFileDialog
from PyQt5.QtGui import  QDoubleValidator
import logging
from pathlib import Path
import time
from datetime import datetime
import importlib

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
        mapping = pd.read_csv(self.loc/'port_map.csv')
        self.mapping = mapping.set_index('name')['port'].fillna("")

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

class NIDIChanThread(QThread):
    """
    PYQT compatible thread for continuously asynchronously monitoring NI digital input ports
    using change detection timing. The thread will emit a custom signal called state_updated 
    whenever a change detection event occurs (rising and falling edge). the signal will contain
    a pandas series mapping ports to their current state
    """
    
    state_updated = pyqtSignal(object)

    def __init__(self, ports, falling_edge = True):
        super(NIDIChanThread, self).__init__()
        self.ports = ports
        self.falling_edge = falling_edge

    def run(self):
        with Task() as task:         
            for name, port in self.ports.items():
                task.di_channels.add_di_chan(port, name_to_assign_to_lines = name)
            port_str = ', '.join(self.ports.tolist())
            if self.falling_edge:
                task.timing.cfg_change_detection_timing(rising_edge_chan = port_str, 
                                                        falling_edge_chan = port_str,
                                                        sample_mode = constants.AcquisitionType.CONTINUOUS)
            else:
                task.timing.cfg_change_detection_timing(rising_edge_chan = port_str, 
                                                        sample_mode = constants.AcquisitionType.CONTINUOUS)

            def update_states(task_handle = task._handle, 
                              signal_type = constants.Signal.CHANGE_DETECTION_EVENT,
                              callback_data = 1):
                data = pd.Series(task.read(), index = self.ports.index)
                self.state_updated.emit(data)
                return 0
            task.register_signal_event(constants.Signal.CHANGE_DETECTION_EVENT, update_states)
            task.start()
            logging.debug(f"beam thread started")
            while True:
                time.sleep(.1)

class RewardDeliveryThread(QThread):

    def __init__(self, parent, valve, typ, lick_thresh, bout_thresh, lick_triggered):
        super(RewardDeliveryThread, self).__init__()
        self.parent = parent
        self.valve = valve
        if typ == 'small':
            self.dur = float(self.valve.small_pulse_frac.text()) * float(self.valve.dur.text())/1000.
        else:
            self.dur = float(self.valve.dur.text())/1000.
        self.lick_thresh = lick_thresh
        self.lick_triggered = lick_triggered
        self.bout_thresh = bout_thresh

    def run(self):
        if self.lick_triggered:
            vopen = False
            querying = True
            while querying:
                if (self.parent.trial_lick_n>0) and ((self.parent.trial_lick_n % self.lick_thresh) == 0) and not vopen:
                    self.valve.open_valve()
                    vopen_t = datetime.now()
                    vopen = True
                elif vopen:
                    t = datetime.now()
                    t_since_open = (t - vopen_t).total_seconds()
                    t_since_last_lick = (t - self.parent.prev_lick).total_seconds()
                    if t_since_last_lick >= self.bout_thresh:
                        self.valve.close_valve()
                        vopen = False
                        self.trial_lick_n = 0
                    if t_since_open>=self.dur:
                        self.valve.close_valve()
                        vopen = False
                        querying = False
        else:
            self.valve.pulse_valve(self.dur)



class ValveControl(QWidget):
    def __init__(self, parent, port, valve_name, purge_port, flush_port, bleed_port1, bleed_port2):
        super(ValveControl, self).__init__()
        self.parent = parent
        self.port = port
        self.valve_in_use = False
        self.valve_name = valve_name
        vlayout= QVBoxLayout()
        valve_label = QLabel(self.valve_name)
        vlayout.addWidget(valve_label)

        
        open_btn  = QPushButton("Open")
        open_btn.clicked.connect(self.open_valve)
        vlayout.addWidget(open_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close_valve)
        vlayout.addWidget(close_btn)

        pulse_layout = QHBoxLayout()
        dur_label = QLabel("Pulse Duration (ms)")
        self.dur = QLineEdit()
        self.dur.setValidator(QDoubleValidator())
        self.dur.setText("400")

        pulse_btn = QPushButton("Pulse")
        pulse_btn.clicked.connect(self.single_pulse)
        pulse_layout.addWidget(dur_label)
        pulse_layout.addWidget(self.dur)
        pulse_layout.addWidget(pulse_btn)
        vlayout.addLayout(pulse_layout)

        small_pulse_layout = QHBoxLayout()
        small_pulse_edit_label = QLabel("Small Pulse Fraction")
        self.small_pulse_frac = QLineEdit()
        only_frac = QDoubleValidator(0.,1., 6, notation = QDoubleValidator.StandardNotation)
        self.small_pulse_frac.setText("0.6")
        self.small_pulse_frac.setValidator(only_frac) # this doesn't seem to be working for some reason
        small_pulse_btn = QPushButton("Small Pulse")
        small_pulse_btn.clicked.connect(self.small_pulse)
        small_pulse_layout.addWidget(small_pulse_edit_label)
        small_pulse_layout.addWidget(self.small_pulse_frac)
        small_pulse_layout.addWidget(small_pulse_btn)
        vlayout.addLayout(small_pulse_layout)

        pulse_mult_layout = QHBoxLayout()
        pulse_mult_num_label =QLabel("Number of Pulses")
        self.pulse_mult_num = QSpinBox(value = 20, minimum = 1, singleStep = 1)
        pulse_multiple_btn = QPushButton("Pulse Many")
        pulse_multiple_btn.clicked.connect(self.pulse_multiple)
        pulse_mult_layout.addWidget(pulse_mult_num_label)
        pulse_mult_layout.addWidget(self.pulse_mult_num)
        pulse_mult_layout.addWidget(pulse_multiple_btn)
        vlayout.addLayout(pulse_mult_layout)      
        self.setLayout(vlayout)

        with Task() as task:
            task.do_channels.add_do_chan(purge_port)
            task.do_channels.add_do_chan(flush_port)
            task.do_channels.add_do_chan(bleed_port1)
            task.do_channels.add_do_chan(bleed_port2)
            task.do_channels.add_do_chan(self.port)
            task.write([True, True, False, False, True], auto_start = True)
            task.wait_until_done()

    def single_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.pulse_valve(self.port, float(self.dur.text()))
            self.valve_in_use = False


    def small_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.pulse_valve(self.port, float(self.small_pulse_frac.text()) * float(self.dur.text()))
            self.valve_in_use = False
        pass

    def pulse_multiple(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            for _ in range(self.pulse_mult_num.value()):
                self.pulse_valve(self.port, float(self.dur.text()))
                time.sleep(.2)

            self.valve_in_use = False

    def open_valve(self):
        if not self.valve_in_use:
            digital_write(self.port, False)
            self.parent.log(f"{self.valve_name} open")
        return

    def close_valve(self):
        if not self.valve_in_use:
            digital_write(self.port, True)
            self.parent.log(f"{self.valve_name} close")
        return

    def pulse_valve(self, dur):
        if dur>0:
            digital_write(self.port, False)
            self.parent.log(f"port {self.valve_name} open")
            time.sleep(dur/1000.) # i should prob do this asynchronously.
            digital_write(self.port, True)
            self.parent.log(f"port {self.valve_name} closed")


def digital_write(port, value):
    with Task() as task:
        task.do_channels.add_do_chan(port)
        task.write(value, auto_start = True)
        task.wait_until_done()
