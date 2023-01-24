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
        self.beams['arm'] = "" # either right, left, home, sleep
        # self.beam_thread = DIChanThread(beam_ports)
        # self.beam_thread.state_updated.connect(self.update_display)
        # self.beam_thread.start()

        vlayout = QVBoxLayout()
        for i in range(2):
            btn = QPushButton()
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

        hlayout = QHBoxLayout()
        beam_buttons = {}
        for beam, port in beam_ports.items():
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
        for i in range(8):
            btn = QPushButton()
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
    
        self.beams['button'] = pd.Series(beam_buttons)
        self.layout.addLayout(vlayout)

    def update_display(self, data):
        prev = self.beams.state.values
        changed = np.where(prev != data)[0]
        for c in changed:
            self.beams['button'].iloc[c].toggle()
        self.beams['state'] = data
        logging.debug(prev)
        logging.debug(data)