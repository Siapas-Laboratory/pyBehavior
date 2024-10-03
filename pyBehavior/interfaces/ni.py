import pandas as pd
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSpinBox, QCheckBox, QFrame
from PyQt5.QtGui import  QDoubleValidator
import time
from datetime import datetime
import nidaqmx
import logging
import time
from pyBehavior.gui import RewardWidget
import socket


def daqmx_supported():
    try:
        with nidaqmx.Task() as task: pass
        return True
    except (nidaqmx._lib.DaqNotFoundError, nidaqmx.errors.DaqNotSupportedError):
        return False
        


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
            self.tasks[dev] = {'task_handle': nidaqmx.Task(),
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
    with nidaqmx.Task() as task:
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

        pulse_layout = QHBoxLayout()
        amt_label = QLabel("Pulse Amount (mL)")
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

        with nidaqmx.Task() as task:
            task.do_channels.add_do_chan(purge_port)
            task.do_channels.add_do_chan(flush_port)
            task.do_channels.add_do_chan(bleed_port1)
            task.do_channels.add_do_chan(bleed_port2)
            task.do_channels.add_do_chan(self.port)
            task.write([True, True, False, False, True], auto_start = True)
            task.wait_until_done()
    
    def single_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.trigger_reward(float(self.amt.text()))
            self.valve_in_use = False

    def small_pulse(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            self.trigger_reward(self.port, float(self.small_pulse_frac.text()) * float(self.amt.text()))
            self.valve_in_use = False
        pass

    def pulse_multiple(self):
        if not self.valve_in_use:
            self.valve_in_use = True
            for _ in range(self.pulse_mult_num.value()):
                self.trigger_reward(float(self.amt.text()))
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
    
    def trigger_reward(self, amount, sync = False):
        dur = amount/float(self.flow_rate.text())
        if dur > 0:
            if sync:
                digital_write(self.widget.port, False)
                time.sleep(dur) # i should prob do this asynchronously.
                digital_write(self.widget.port, True)
            else:
                self.reward_thread = self.RewardDeliveryThread(self, dur)
                self.reward_thread.start()

    class RewardDeliveryThread(QThread):
        def __init__(self, widget, dur):
            super(NIRewardControl.RewardDeliveryThread, self).__init__()
            self.widget = widget
            self.dur = dur

        def run(self):
            digital_write(self.widget.port, False)
            time.sleep(self.dur) # i should prob do this asynchronously.
            digital_write(self.widget.port, True)


class EventstringSender(QFrame):
    def __init__(self, parent, event_line_name:str, event_line_addr:str, ip:str = socket.gethostbyname(socket.gethostname()), port:int = 2345):
        super(EventstringSender, self).__init__()

        self.parent = parent
        self.event_line_addr = event_line_addr
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Event Line: {event_line_name}"))
        layout.addWidget(QLabel("Eventstring Destination"))
        port_layout = QHBoxLayout()
        ip_label = QLabel(f"IP: ")
        self.ip = QLineEdit()
        self.ip.setText(ip)
        port_label = QLabel("PORT: ")
        self.port = QLineEdit()
        self.port.setValidator(QDoubleValidator())
        self.port.setText(f"{port}")

        port_layout.addWidget(ip_label)
        port_layout.addWidget(self.ip)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port)
        layout.addLayout(port_layout)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.setLayout(layout)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(2)
    
    def bind_port(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, msg):
        digital_write(self.event_line_addr, True)
        if self.sock is not None:
            self.sock.sendto(msg.encode("utf8"), (self.ip.text(), int(self.port.text())))
        self.parent.logger.info(msg)
        digital_write(self.event_line_addr, False)