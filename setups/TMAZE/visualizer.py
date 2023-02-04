from nidaqmx import constants, Task
import logging
import matplotlib.pyplot as plt
import time

from PyQt5.QtCore import QThread, pyqtSignal, Qt
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog, QRadioButton
sys.path.append("../")
from utils import *


class ValveControl(QWidget):
    def __init__(self, port, valve_name):
        super(ValveControl, self).__init__()
        vlayout= QVBoxLayout()
        valve_label = QLabel(valve_name)
        vlayout.addWidget(valve_label)
        hlayout = QHBoxLayout()
        dur_label = QLabel("Pulse Duration (ms)")
        dur = QLineEdit()
        hlayout.addWidget(dur_label)
        hlayout.addWidget(dur)
        open_btn = QPushButton("Open")
        close_btn = QPushButton("Close")
        pulse_btn = QPushButton("Pulse")
        pulse_multiple = QPushButton("Pulse Many")
        vlayout.addLayout(hlayout)
        vlayout.addWidget(open_btn)
        vlayout.addWidget(close_btn)
        vlayout.addWidget(pulse_btn)
        vlayout.addWidget(pulse_multiple)
        self.setLayout(vlayout)
        #TODO: need small pulse button, small pulse fraction, and option to adjust number of pulses
        # ideally TMAZEVis should also keep track of these settings so when it calls trigger_reward it knows the correct parameters for each valve
        # should these settings be saved as well? both in results and as defaults?

        

class TMAZEVis(SetupVis):

    def __init__(self, loc):
        super(TMAZEVis, self).__init__(loc)
        self.buildUI()

    def buildUI(self):
        beam_ports = self.mapping.loc[self.mapping.index.str.contains("beam")]
        self.beams = beam_ports.rename('port').to_frame()

        self.beams['state'] = np.zeros((len(beam_ports),), dtype = bool)
        right_arm = [f'beam{i}' for i in range(1,9)]
        left_arm = [f'beam{i}' for i in range(9,17)]
        bottom_arm = [f'beam{i}' for i in range(17,28)]
        sleep_arm = ['beam29', 'beam28']

        self.beams.loc[right_arm, 'arm'] = "right"
        self.beams.loc[left_arm, 'arm'] = "left"
        self.beams.loc[bottom_arm, 'arm'] = "bottom"
        self.beams.loc[sleep_arm, 'arm'] = "sleep"

        self.beam_thread = DIChanThread(beam_ports)
        self.beam_thread.state_updated.connect(self.register_state_change)
        
        beam_buttons = {}
        vlayout = QVBoxLayout()
        stem_valve = ValveControl(self.mapping.loc['juicer_valve2'], 'juicer_valve2')
        vlayout.addWidget(stem_valve)
        for beam in bottom_arm:
            btn = QPushButton(beam)
            btn.setFixedSize(100, 100)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 50;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            vlayout.addWidget(btn, alignment = Qt.AlignHCenter)
            beam_buttons.update({beam: btn})

        hlayout = QHBoxLayout()

        for beam in right_arm[::-1] + left_arm:
            btn = QPushButton(beam)
            btn.setFixedSize(100, 100)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 50;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            hlayout.addWidget(btn, alignment = Qt.AlignVCenter)
            beam_buttons.update({beam: btn})
        
        vlayout.addLayout(hlayout)
        for beam in sleep_arm:
            btn = QPushButton(beam)
            btn.setFixedSize(100, 100)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 50;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            vlayout.addWidget(btn, alignment = Qt.AlignHCenter)
            beam_buttons.update({beam: btn})
        
    
        self.beams['button'] = pd.Series(beam_buttons)
        self.beam_thread.start()
        self.layout.addLayout(vlayout)

    def trigger_reward(self, port, typ = 'full'):
        # get the appropriate pulse duration for this port
        print(f"pulsing port {port}, {typ}")

    def register_state_change(self, data):
        if self.running:
            self.state_machine.handle_input(self.beams.state, data)
        prev = self.beams.state
        changed = data[self.beams.state != data].index
        for c in changed:
            self.beams.loc[c,'button'].toggle()
        self.beams['state'] = data
        logging.debug(prev)
        logging.debug(data)
    
    def remap(self):
        # need to delete all ui elements then rerun buildUI
        pass
    
    def validate_map(self, map_file):
        return True
