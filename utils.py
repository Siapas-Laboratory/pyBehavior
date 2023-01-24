import numpy as np
import pandas as pd
from nidaqmx import constants, Task
from PyQt5.QtCore import QThread, pyqtSignal
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
import logging
import inspect
from pathlib import Path



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
        _, _, mapping = load_mapping(Path(loc)/'params.npy')
        self.mapping = mapping.set_index('name')['port'].fillna("")
        container = QWidget()
        self.layout = QVBoxLayout()

        # need 2 combo boxes, one to select protocol
        # another to select the port-mapping
        self.prot_select = QComboBox()
        self.layout.addWidget(self.prot_select)
        container.setLayout(self.layout)
        self.setCentralWidget(container)

class DIChanThread(QThread):

    state_updated = pyqtSignal(object)

    def __init__(self, ports):
        super(DIChanThread, self).__init__()
        self.beam_ports = ports

    def run(self):
        with Task() as task:         
            for name, port in self.beam_ports.items():
                task.di_channels.add_di_chan(port, name_to_assign_to_lines = name)
            port_str = ', '.join(self.beam_ports.tolist())
            task.timing.cfg_change_detection_timing(rising_edge_chan = port_str, 
                                                    falling_edge_chan = port_str,
                                                    sample_mode=constants.AcquisitionType.CONTINUOUS)
            def update_states(task_handle = task._handle, 
                              signal_type = constants.Signal.CHANGE_DETECTION_EVENT,
                              callback_data = 1):
                self.state_updated.emit(task.read())
                return 0
            task.register_signal_event(constants.Signal.CHANGE_DETECTION_EVENT, update_states)
            task.start()
            logging.debug(f"beam thread started")
            while True:
                time.sleep(.1)