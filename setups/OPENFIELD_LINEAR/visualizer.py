import sys
sys.path.append("../")
from PyQt5.QtWidgets import  QHBoxLayout
from utils.ui import *
from utils.rpi import *
import socket
import time

class OPENFIELD_LINEAR(SetupVis):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.sock = None
        self.buildUI()
        self.client.run_command('toggle_auto_fill', {'on': True})

    def buildUI(self):

        port_layout = QHBoxLayout()
        ip = QLabel(f"IP: {socket.gethostbyname(socket.gethostname())}")
        self.pos_port = QLineEdit()
        self.pos_port.setValidator(QDoubleValidator())
        self.pos_port.textChanged.connect(self.bind_port)
        self.pos_port.setText("1234")
        port_layout.addWidget(ip)
        port_layout.addWidget(self.pos_port)
        self.layout.addLayout(port_layout)

        pos_layout =  QHBoxLayout()
        poslabel = QLabel("Position")
        self.pos = QLabel("")
        pos_layout.addWidget(poslabel)
        pos_layout.addWidget(self.pos)
        self.layout.addLayout(pos_layout)

        self.mod1 = RPIRewardControl(self.client, 'module1')
        self.mod2 = RPIRewardControl(self.client, 'module2')
        self.reward_modules.update({'mod1': self.mod1, 
                                    'mod2': self.mod2})

        #format widgets
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(self.mod1)
        mod_layout.addWidget(self.mod2)
        self.layout.addLayout(mod_layout)

        # start digital input threads
        # threads to monitor licking
        self.lick1_thread = RPILickThread(self.client, "module1")
        self.lick1_thread.state_updated.connect(lambda x: self.register_lick(x, 'module1'))
        self.lick1_thread.start()

        self.lick2_thread = RPILickThread(self.client, "module2")
        self.lick2_thread.state_updated.connect(lambda x: self.register_lick(x, 'module2'))
        self.lick2_thread.start()

        self.pos_thread = Position(self)
        self.pos_thread.start()
    
    def bind_port(self, port):
        print(port)
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", int(port)))


    def register_lick(self, data, module):
        msg = f'{module} lick {data}'
        print(msg)
        self.log(msg)

class Position(QThread):
    def __init__(self, parent):
        super(Position, self).__init__()
        self.parent = parent
    
    def run(self):
        while True:
            if self.parent.sock:
                p = self.parent.sock.recv(1024).decode()
                print(p)
                self.parent.pos.setText(p)
                time.sleep(.05)