from PyQt5.QtCore import QThread, pyqtSignal, QObject
import numpy as np
import socket
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QGroupBox
from PyQt5.QtGui import  QDoubleValidator
import ast


class Position(QGroupBox):

    new_position = pyqtSignal(list, name = 'newPosition')

    def __init__(self, port:int = 1234):

        super(Position, self).__init__()
        self.pos_thread = PositionThread(port)
        self.pos_thread.new_position.connect(lambda x: self.new_position.emit(x))

        layout = QVBoxLayout()
        port_layout = QHBoxLayout()
        ip = QLabel(f"IP: {socket.gethostbyname(socket.gethostname())}")
        self.port = QLineEdit()
        self.port.setValidator(QDoubleValidator())
        self.port.setText(f"{port}")
        self.port.textChanged.connect(lambda x: self.pos_thread.bind_port(x))
        port_layout.addWidget(ip)
        port_layout.addWidget(self.port)
        layout.addLayout(port_layout)

        pos_layout =  QHBoxLayout()
        poslabel = QLabel("Position")
        self.pos = QLabel("")
        pos_layout.addWidget(poslabel)
        pos_layout.addWidget(self.pos)
        layout.addLayout(pos_layout)

        self.setLayout(layout)

    def start(self):
        self.pos_thread.start()

class PositionThread(QThread):
    
    new_position = pyqtSignal(list, name = 'newPosition')

    def __init__(self, port, buff_size = 10):
        super(PositionThread, self).__init__()
        self.sock = None
        self.bind_port(port)
        self.pos_buffer = []
        self.conf_buffer = []

    def bind_port(self, port):
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", int(port)))
    
    def run(self):
        while True:
            if self.sock:
                pos = ast.literal_eval(self.sock.recv(1024).decode())
                self.pos_buffer.append(np.array([i[0] for i in pos[0]]))
                self.conf_buffer.append(np.array([i[1] for i in pos[0]]))
                self.pos_buffer = self.pos_buffer[-5:]
                self.conf_buffer = self.conf_buffer[-5:]
                weighted_pos = np.array(self.pos_buffer) * np.array(self.conf_buffer)[:,:,None]
                pos = weighted_pos.sum(axis=0)/np.array(self.conf_buffer).sum(axis=0)[:,None]
                pos = pos.mean(axis=0).tolist()
                self.new_position.emit(pos[::-1])
