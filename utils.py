import numpy as np
import pandas as pd
from nidaqmx import constants, Task
from PyQt5.QtCore import QThread, pyqtSignal
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
import logging
import inspect
from pathlib import Path
import time



def load_mapping(params_file):
    params = np.load(params_file, allow_pickle = True).item()
    map_file = params['map-file']
    # load the currently selected map file
    # TODO: need to wrap this in a try except clause to make sure 'port' is an existing  column
    # just in case people want to edit the csv in excel
    mapping = pd.read_csv(map_file)

    return params, map_file, mapping


class SetupVis(QMainWindow):
    def __init__(self, loc):
        super(SetupVis, self).__init__()
        self.loc = Path(loc)
        self.params, _, mapping = load_mapping(self.loc/'params.npy')
        if not self.validate_map(self.params['map-file']):
            raise Exception("invalid map file")
        self.mapping = mapping.set_index('name')['port'].fillna("")

        # validate the mapping here
        container = QWidget()
        self.layout = QVBoxLayout()
        self.menu_layout = QHBoxLayout()

        protocols = [ i.stem for i in (self.loc/'protocols').iterdir() ]
        self.prot_select = QComboBox()
        self.prot_select.addItems([""] + protocols)
        self.prot_select.currentIndexChanged.connect(self.change_protocol)

        self.map_select = QComboBox()
        self.map_select.addItems([i.stem for i in Path('port-mappings').iterdir()])
        self.map_select.setCurrentText(Path(self.params['map-file']).stem)
        self.map_select.currentIndexChanged.connect(self.update_map)

        self.start_btn = QPushButton("start")
        self.start_btn.setCheckable(True)
        self.running = False
        self.start_btn.clicked.connect(self.start_protocol)

        self.stop_btn = QPushButton("stop")
        # need a start and stop button

        self.menu_layout.addWidget(self.prot_select)
        self.menu_layout.addWidget(self.map_select)
        self.layout.addLayout(self.menu_layout)

        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.state_machine = None

    def start_protocol(self):
        if not self.running:
            if len(self.prot_select.currentText()>0):
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

    def update_map(self):
        new_map =  f'port-mappings/{str(self.map_select.currentText())}.csv'
        if self.validate_map(new_map):
            self.params['map-file'] = new_map
            np.save(self.loc/'params.npy', self.params)
            self.mapping = pd.read_csv(new_map).set_index('port')['name'].fillna("")
            self.remap()

    def remap(self):
        print("WARNING: no remap() method has been defined")
        pass

    def validate_map(self, map_file):
        print("WARNING: no validate_map() method has been defined")
        return True
    
    def change_protocol(self):
        # import and create the statemachine
        prot_name = self.prot_select.currentText()
        if len(prot_name)>0:
            prot = (self.loc/'protocols'/prot_name).as_posix()
            import importlib
            setup_mod = importlib.import_module(prot.replace('/','.'))
            state_machine = getattr(setup_mod, "TMAZE") # need to fix this line
            self.state_machine = state_machine()
        else:
            self.state_machine = None

class DIChanThread(QThread):

    state_updated = pyqtSignal(object)

    def __init__(self, ports):
        super(DIChanThread, self).__init__()
        self.ports = ports

    def run(self):
        with Task() as task:         
            for name, port in self.beam_ports.items():
                task.di_channels.add_di_chan(port, name_to_assign_to_lines = name)
            port_str = ', '.join(self.beam_ports.tolist())
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


def pulse_valve(port, dur):
    pass