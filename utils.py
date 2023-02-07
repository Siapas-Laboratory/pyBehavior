import numpy as np
import pandas as pd
from nidaqmx import constants, Task
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QSpinBox
from PyQt5.QtGui import  QDoubleValidator
import logging
from pathlib import Path
import time


class SetupVis(QMainWindow):
    def __init__(self, loc):
        super(SetupVis, self).__init__()
        self.loc = Path(loc)
        mapping = pd.read_csv(self.loc/'port_map.csv')
        self.mapping = mapping.set_index('name')['port'].fillna("")

        # validate the mapping here
        container = QWidget()
        self.layout = QVBoxLayout()
        self.menu_layout = QHBoxLayout()

        protocols = [ i.stem for i in (self.loc/'protocols').iterdir() ]
        self.prot_select = QComboBox()
        self.prot_select.addItems([""] + protocols)
        self.prot_select.currentIndexChanged.connect(self.change_protocol)

        self.start_btn = QPushButton("start")
        self.start_btn.setCheckable(True)
        self.running = False
        self.start_btn.clicked.connect(self.start_protocol)

        self.stop_btn = QPushButton("stop")
        self.stop_btn.clicked.connect(self.stop_protocol)

        self.menu_layout.addWidget(self.prot_select)
        self.menu_layout.addWidget(self.start_btn)
        self.menu_layout.addWidget(self.stop_btn)
        self.layout.addLayout(self.menu_layout)

        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.state_machine = None

    def start_protocol(self):
        if not self.running:
            if len(self.prot_select.currentText())>0:
                self.running = True
                # TODO: need a file dialog to create a file to save the data to
            else:
                self.start_btn.toggle()
        else:
            self.stop_protocol()

    def stop_protocol(self):
        self.running = False
        if self.start_btn.isChecked():
            self.start_btn.toggle()

    def change_protocol(self):
        # import and create the statemachine
        prot_name = self.prot_select.currentText()
        if len(prot_name)>0:
            prot = (self.loc/'protocols'/prot_name).as_posix()
            import importlib
            setup_mod = importlib.import_module(prot.replace('/','.'))
            state_machine = getattr(setup_mod, prot_name)
            self.state_machine = state_machine(self)
        else:
            self.state_machine = None



class DIChanThread(QThread):

    state_updated = pyqtSignal(object)

    def __init__(self, ports):
        super(DIChanThread, self).__init__()
        self.ports = ports

    def run(self):
        with Task() as task:         
            for name, port in self.ports.items():
                task.di_channels.add_di_chan(port, name_to_assign_to_lines = name)
            port_str = ', '.join(self.ports.tolist())
            task.timing.cfg_change_detection_timing(rising_edge_chan = port_str, 
                                                    falling_edge_chan = port_str,
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

class ValveControl(QWidget):
    def __init__(self, port, valve_name):
        super(ValveControl, self).__init__()
        self.port = port
        self.valve_in_use = False
        vlayout= QVBoxLayout()
        valve_label = QLabel(valve_name)
        vlayout.addWidget(valve_label)

        
        open_btn  = QPushButton("Open")
        vlayout.addWidget(open_btn)

        close_btn = QPushButton("Close")
        vlayout.addWidget(close_btn)

        pulse_layout = QHBoxLayout()
        dur_label = QLabel("Pulse Duration (ms)")
        self.dur = QLineEdit()
        self.dur.setValidator(QDoubleValidator())

        pulse_btn = QPushButton("Pulse")
        pulse_btn.clicked.connect(self.pulse)
        pulse_layout.addWidget(dur_label)
        pulse_layout.addWidget(self.dur)
        pulse_layout.addWidget(pulse_btn)
        vlayout.addLayout(pulse_layout)

        small_pulse_layout = QHBoxLayout()
        small_pulse_edit_label = QLabel("Small Pulse Fraction")
        self.small_pulse_frac = QLineEdit()
        only_frac = QDoubleValidator()
        only_frac.setRange(0,1)
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

    def pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            pulse_valve(self.port, float(self.dur.text()))
            self.valve_in_use = False


    def small_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            pulse_valve(self.port, float(self.small_pulse_frac.text()) * float(self.dur.text()))
            self.valve_in_use = False
        pass

    def pulse_multiple(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            for _ in range(self.pulse_mult_num.value()):
                pulse_valve(self.port, float(self.dur.text()))
                time.sleep(.5)
            self.valve_in_use = False

    def open_valve(self):
        if not self.valve_in_use:
            return
        return

    def close_valve(self):
        if not self.valve_in_use:
            return
        return


        #TODO: should these settings be saved as well? both in results and as defaults?



def pulse_valve(port, dur):
    print("opening valve")
    #TODO: actually pulse the valve
    time.sleep(dur/1000.)
    print("closing valve")
    pass