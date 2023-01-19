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

    def __init__(self, beam_ports):
        super(BeamThread, self).__init__()
        self.beam_ports = beam_ports

    def run(self):
        with Task() as task:         
            for beam, port in self.beam_ports.items():
                task.di_channels.add_di_chan(port, name_to_assign_to_lines = beam)
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



# # i should probably subclass QMainWindow to define a template for these protocol GUIS that can be 
# # subclassed for writing  protocols

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        # TODO: need to validate that a valid port-map file has been selected
        _, _, mapping = load_mapping()
        mapping = mapping.set_index('name')['port'].fillna("")
        beam_ports = mapping.loc[mapping.index.str.contains("beam")]
        self.beams = beam_ports.rename('port').to_frame()
        self.beams['state'] = np.zeros((len(beam_ports),), dtype = bool)
        self.beam_thread = BeamThread(beam_ports)
        self.beam_thread.state_updated.connect(self.update_display)
        self.beam_thread.start()

        layout = QHBoxLayout()
        beam_buttons = {}
        for beam, port in beam_ports.items():
            btn = QPushButton(beam)
            btn.setStyleSheet("QPushButton"
                              "{"
                              "background-color : lightblue;"
                              "}"
                              "QPushButton::checked"
                              "{"
                              "background-color : red;"
                              "}")
            btn.setCheckable(True)
            layout.addWidget(btn)
            beam_buttons.update({beam: btn})

        self.beams['button'] = pd.Series(beam_buttons)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def update_display(self, data):
        prev = self.beams.state.values
        changed = np.where(prev != data)[0]
        for c in changed:
            self.beams['button'].iloc[c].toggle()
        self.beams['state'] = data
        logging.debug(prev)
        logging.debug(data)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(640, 480)
    window.show()
    sys.exit(app.exec_())
