from nidaqmx import constants, Task
import logging
import matplotlib.pyplot as plt
import time

from PyQt5.QtCore import QThread, pyqtSignal, Qt
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog, QRadioButton
sys.path.append("../")
from utils import *


class TMAZEVis(SetupVis):

    def __init__(self):
        super(TMAZEVis, self).__init__(Path(__file__).resolve().parent.as_posix())
        # TODO: need to validate that a valid port-map file has been selected
        beam_ports = self.mapping.loc[self.mapping.index.str.contains("beam")]
        
        self.beams = beam_ports.rename('port').to_frame()
        self.beams['state'] = np.zeros((len(beam_ports),), dtype = bool)
        right_arm = [f'beam{i}' for i in range(1,9)]
        left_arm = [f'beam{i}' for i in range(9,17)]
        bottom_arm = [f'beam{i}' for i in range(17,28)]
        sleep_arm = ['beam28', 'beam29']

        self.beams.loc[right_arm, 'arm'] = "right"
        self.beams.loc[left_arm, 'arm'] = "left"
        self.beams.loc[bottom_arm, 'arm'] = "bottom"
        self.beams.loc[sleep_arm, 'arm'] = "sleep"

        self.beam_thread = DIChanThread(beam_ports)
        self.beam_thread.state_updated.connect(self.register_state_change)
        
        beam_buttons = {}
        vlayout = QVBoxLayout()
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

        hlayout = QHBoxLayout()
        for beam in left_arm[::-1] + right_arm:
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
        for beam in bottom_arm[::-1]:
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

    def register_state_change(self, data):
        prev = self.beams.state.values
        changed = np.where(prev != data)[0]
        for c in changed:
            self.beams['button'].iloc[c].toggle()
        self.beams['state'] = data
        logging.debug(prev)
        logging.debug(data)