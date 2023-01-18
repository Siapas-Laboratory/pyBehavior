from nidaqmx import constants, Task
import logging
import matplotlib.pyplot as plt
import time
from PyQt5.QtCore import QThread, pyqtSignal
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
from utils import *

logging.basicConfig(format = "%(asctime)s-%(levelname)s: %(message)s", level = logging.DEBUG)

class BeamThread(QThread):

    state_updated = pyqtSignal(object)

    def __init__(self, beam, port):
        super(BeamThread, self).__init__()
        self.port = port
        self.beam = beam

    def run(self):
        with Task() as task:
            task.di_channels.add_di_chan(self.port, name_to_assign_to_lines = self.beam)
            task.timing.cfg_change_detection_timing(rising_edge_chan = self.port, 
                                                    falling_edge_chan = self.port,
                                                    sample_mode=constants.AcquisitionType.CONTINUOUS)
            def update_states(task_handle = task._handle, 
                              signal_type = constants.Signal.CHANGE_DETECTION_EVENT,
                              callback_data = 1):
                self.state_updated.emit(f"{self.beam}\n{task.read()}")
            task.register_signal_event(constants.Signal.CHANGE_DETECTION_EVENT, update_states)
            task.start()
            logging.debug(f"started {self.beam}")
            while True:
                time.sleep(.1)



# # i should probably subclass QMainWindow to define a template for these protocol GUIS that can be 
# # subclassed for writing  protocols

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        # TODO: need to validate that a valid port-map file has been selected
        _, _, mapping = load_mapping()
        mapping = mapping.set_index('name')['port'].fillna("")
        beam_ports = mapping.loc[mapping.index.str.contains("beam")]
        beam_threads = {}

        for beam, port in beam_ports.items():
            #create GUI element
            bt = BeamThread(beam, port) # create thread
            bt.state_updated.connect(self.update_display)
            beam_threads.update({'beam': bt})
            bt.start()

    def update_display(self, data):
        logging.debug(data)
        # given which beam has been affected update the appropriate GUI element



        # we need to acquire one sample at a time from all beam channels
        # compare the state to the current state and if it is different update the gui element

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(640, 480)
    window.show()
    sys.exit(app.exec_())
