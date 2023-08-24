import sys
from PyQt5.QtWidgets import  QHBoxLayout
from utils.ui import *
from utils.rpi import *

class OPENFIELD_LINEAR(SetupVis):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()
        self.client.run_command('toggle_auto_fill', {'on': True})

    def buildUI(self):

        self.mod1 = RPIRewardControl(self.client, 'module1')
        self.mod2 = RPIRewardControl(self.client, 'module2')
        self.reward_modules.update({'mod1': self.mod1, 
                                    'mod2': self.mod2})

        #format widgets
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.mod1)
        hlayout.addWidget(self.mod2)
        self.layout.addLayout(hlayout)

        # start digital input threads
        # threads to monitor licking
        self.lick1_thread = RPILickThread(self.client, "module1")
        self.lick1_thread.state_updated.connect(lambda x: self.register_lick(x, 'module1'))
        self.lick1_thread.start()

        self.lick2_thread = RPILickThread(self.client, "module2")
        self.lick2_thread.state_updated.connect(lambda x: self.register_lick(x, 'module2'))
        self.lick2_thread.start()

    def register_lick(self, data, module):
        msg = f'{module} lick {data}'
        print(msg)
        self.log(msg)