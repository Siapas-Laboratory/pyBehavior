import pandas as pd
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSpinBox, QCheckBox
from PyQt5.QtGui import  QDoubleValidator
import time
from datetime import datetime
from nidaqmx import constants, Task, errors
import logging
import time
from pyBehavior.gui import RewardWidget

class NIDIChan(QObject):

    rising_edge = pyqtSignal(str, name = 'risingEdge')
    falling_edge = pyqtSignal(str, name = 'fallingEdge')

class NIDIDaemon(QObject):

    finished = pyqtSignal(int, name = "finished")

    def __init__(self, fs = 1000):
        super(NIDIDaemon, self).__init__()
        self.fs = fs
        self.tasks = {}
        self.channels = pd.Series([], dtype = object)
        self.running = False
        self.status = 0

    def register(self, channel, name):

        dev = channel.split('/')[0]
        if dev not in self.tasks:
            self.tasks[dev] = {'task_handle': Task(),
                               'channel_names': [name]}
        else:
            self.tasks[dev]['channel_names'].append(name)
        self.tasks[dev]['task_handle'].di_channels.add_di_chan(channel, name_to_assign_to_lines = name)
        self.channels.loc[name] =  NIDIChan()
    
    def run(self):
        self.running = True
        if len(self.tasks)>0:
            # initialize all states as false
            self.state = pd.Series([False]*self.channels.size,
                                   index = self.channels.index)
            try:
                while self.running:
                    _state = self.read()
                    for i in self.channels.loc[_state > self.state].index:
                        self.channels.loc[i].rising_edge.emit(i)
                    for i in self.channels.loc[_state < self.state].index:
                        self.channels.loc[i].falling_edge.emit(i)
                    self.state = _state
                    time.sleep(1/self.fs)
            except:
                self.stop()
                self.status = 2
            finally:
                self.status = 1
        self.finished.emit(self.status)
    
    def read(self):
        state = {}
        for dev in self.tasks:
            names = self.tasks[dev]['channel_names']
            handle = self.tasks[dev]['task_handle']
            if len(names)>1:
                state.update(dict(zip(names, handle.read()))), 
            else:
                state.update({names[0]: handle.read()})

        return pd.Series(state)

    def stop(self):
        self.running = False
        for dev in self.tasks:
            self.tasks[dev]['task_handle'].close()


def digital_write(port, value):
    with Task() as task:
        task.do_channels.add_do_chan(port)
        task.write(value, auto_start = True)
        task.wait_until_done()


class NIRewardControl(RewardWidget):
    def __init__(self, port, name, parent, purge_port, flush_port, bleed_port1, bleed_port2):
        
        super(NIRewardControl, self).__init__()

        self.port = port
        self.name = name
        self.parent = parent
        self.valve_in_use = False
        self.lick_thresh = 3
        self.bout_thresh = .5

        vlayout= QVBoxLayout()
        valve_label = QLabel(self.name)
        vlayout.addWidget(valve_label)
        
        open_btn  = QPushButton("Open")
        open_btn.clicked.connect(self.open_valve)
        vlayout.addWidget(open_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close_valve)
        vlayout.addWidget(close_btn)

        flow_layout = QHBoxLayout()
        flow_label = QLabel("Flow Rate (mL/s)")
        self.flow_rate = QLineEdit()
        self.flow_rate.setText("0.86")
        flow_layout.addWidget(flow_label)
        flow_layout.addWidget(self.flow_rate)
        vlayout.addLayout(flow_layout)

        self.lick_triggered = QCheckBox('Lick Triggered')
        vlayout.addWidget(self.lick_triggered)
        self.lick_triggered.setChecked(False)

        tpulse_layout = QHBoxLayout()
        dur_label = QLabel("Timed Pulse Duration")
        self.dur = QLineEdit()
        self.dur.setValidator(QDoubleValidator())
        self.dur.setText("1")

        tpulse_btn = QPushButton("Timed Pulse")
        tpulse_btn.clicked.connect(self.timed_pulse)
        tpulse_layout.addWidget(dur_label)
        tpulse_layout.addWidget(self.dur)
        tpulse_layout.addWidget(tpulse_btn)
        vlayout.addLayout(tpulse_layout)


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
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
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
    
    def timed_pulse(self):
        dur = float(self.dur.text())
        if dur>0:
            print('opening')
            digital_write(self.port, False)
            time.sleep(dur/1000.) # i should prob do this asynchronously.
            digital_write(self.port, True)
            print('closing')

    def pulse(self, amount):
        dur = amount/float(self.flow_rate.text())
        if dur>0:
            digital_write(self.port, False)
            time.sleep(dur) # i should prob do this asynchronously.
            digital_write(self.port, True)

    def single_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.pulse(float(self.amt.text()))
            self.valve_in_use = False

    def small_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.pulse(self.port, float(self.small_pulse_frac.text()) * float(self.amt.text()))
            self.valve_in_use = False
        pass

    def pulse_multiple(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            for _ in range(self.pulse_mult_num.value()):
                self.pulse(float(self.amt.text()))
                time.sleep(.2)
            self.valve_in_use = False

    def open_valve(self):
        if not self.valve_in_use:
            digital_write(self.port, False)
            self.parent.log(f"{self.name} open")
        return

    def close_valve(self):
        if not self.valve_in_use:
            digital_write(self.port, True)
            self.parent.log(f"{self.name} close")
        return
    
    def trigger_reward(self, small = False):
        if small:
            amount =  float(self.small_pulse_frac.text()) * float(self.amt.text())
        else:
            amount =  float(self.amt.text())
        self.reward_thread = self.RewardDeliveryThread(self, self.parent, amount, self.lick_thresh, 
                                                       self.bout_thresh, self.lick_triggered.checkState())
        self.reward_thread.start()

    class RewardDeliveryThread(QThread):
        def __init__(self, valve, parent, amount, lick_thresh, bout_thresh, lick_triggered):
            super(NIRewardControl.RewardDeliveryThread, self).__init__()
            self.parent = parent
            self.valve = valve
            self.amount = amount
            self.lick_thresh = lick_thresh
            self.lick_triggered = lick_triggered
            self.bout_thresh = bout_thresh

        def run(self):
            if self.lick_triggered:
                vopen = False
                querying = True
                dur = self.amount/float(self.valve.flow_rate.text())
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
                        if t_since_open>=dur:
                            self.valve.close_valve()
                            vopen = False
                            querying = False
            else:
                self.valve.pulse(self.amount)
