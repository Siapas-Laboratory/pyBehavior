from PyQt5.QtCore import QThread, pyqtSignal
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QLabel, QCheckBox
from PyQt5.QtGui import  QDoubleValidator


path_to_rpi_reward_mod = '/Users/nathanielnyema/Downloads/rpi-reward-module/'


class RPIRewardControl(QWidget):

    def __init__(self, client, module):
        super(RPIRewardControl, self).__init__()

        self.module = module
        self.client = client
        self.name = module

        if not self.client.connected:
            self.client.connect()
        
        vlayout= QVBoxLayout()
        valve_label = QLabel(self.name)
        vlayout.addWidget(valve_label)

        #NEED control of syringe type

        self.lick_triggered = QCheckBox('Lick Triggered')
        vlayout.addWidget(self.lick_triggered)
        self.lick_triggered.setChecked(False)

        pulse_layout = QHBoxLayout()
        amt_label = QLabel("Reward Amount (mL)")
        self.amt = QLineEdit()
        self.amt.setValidator(QDoubleValidator())
        self.amt.setText("0.2")

        pulse_btn = QPushButton("Pulse")
        pulse_btn.clicked.connect(self.single_pulse)
        pulse_layout.addWidget(amt_label)
        pulse_layout.addWidget(self.amt)
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
    
    def single_pulse(self):
        self.pulse(float(self.amt.text()))

    def small_pulse(self):
        self.pulse(float(self.small_pulse_frac.text()) * float(self.amt.text()))
        
    def pulse(self, amount):
        try:
            _ = self.client.trigger_reward(self.module, amount)
        except:
            pass

    def trigger_reward(self, small = False):
        if small:
            amount =  float(self.small_pulse_frac.text()) * float(self.amt.text())
        else:
            amount =  float(self.amt.text())
        if self.lick_triggered.checkState():
            _ = self.client.lick_triggered_reward(self.module, amount)
        else:
            _ = self.pulse(self.module, amount)

class RPILickThread(QThread):
    state_updated = pyqtSignal(object)
    def __init__(self, client, module):
        super(RPILickThread, self).__init__()
        assert client.connected
        self.client = client
        self.module = module
    
    def run(self):
        prev_licks = 0
        while True:
            licks = int(self.client.get_prop(self.module, 'licks'))
            if licks!=prev_licks:
                self.state_updated.emit(licks)
