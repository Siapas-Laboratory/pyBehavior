from pyBehavior.interfaces.rpi.remote import *
from pyBehavior.interfaces.ni import *

from pyBehavior.gui import *

class setup1(SetupGUI):
    def __init__(self):
        super(setup1, self).__init__(Path(__file__).parent.resolve())

        pump = PumpConfig(self.client, 'pump1', self, ['module1'])
        self.layout.addWidget(pump)
        
        reward_module = RPIRewardControl(self.client, 'module1', self)
        self.layout.addWidget(reward_module)
        self.register_reward_module('module1', reward_module)
        self.register_state_machine_input(reward_module.new_licks, 'lick',
                                          before = lambda x: self.log(f"{x} licks", raise_event_line=False))
