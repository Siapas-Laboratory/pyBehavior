import sys
from PyQt5.QtWidgets import  QHBoxLayout
from utils.ui import SetupVis
from utils.rpi import RPIRewardControl, RPILickThread, path_to_rpi_reward_mod
import sys
sys.path.append(path_to_rpi_reward_mod)
from client import remote_connect


class OPENFIELD_LINEAR(SetupVis):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.client = remote_connect()
        self.buildUI()

    def buildUI(self):

        self.mod1 = RPIRewardControl(self, self.client, self.mapping.loc['module1'])
        self.mod2 = RPIRewardControl(self, self.client, self.mapping.loc['module1'])
        self.reward_modules.update({'mod1': self.mod1, 'mod2': self.mod2})

        #format widgets
        hlayout.addWidget(self.mod1_control)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.mod1_control)
        hlayout.addWidget(self.mod2_control)
        self.layout.addLayout(hlayout)

        # start digital input threads
        # threads to monitor licking
        self.lick1_thread = RPILickThread(self.client, self.mapping.loc[["module1"]])
        self.lick1_thread.state_updated.connect(self.register_lick)
        self.lick1_thread.start()

        self.lick2_thread = RPILickThread(self.client, self.mapping.loc[["module2"]])
        self.lick2_thread.state_updated.connect(lambda x: self.register_lick(x, 'module2'))
        self.lick2_thread.start()

    def register_lick(self, data, module):
        self.log(f'{module} lick')
  