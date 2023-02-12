from statemachine import StateMachine, State
from PyQt5.QtCore import pyqtSignal

import sys
sys.path.append("../")
from utils import *


class linear_track(StateMachine):

    sleep = State("sleep", initial=True)
    a_reward= State("a_reward")
    b_reward= State("b_reward")

    beamA =  ( sleep.to(a_reward,  after = "deliver_reward") 
               | b_reward.to(a_reward,  after = "deliver_reward") 
               | a_reward.to.itself() 
    )


    beamB =  ( sleep.to(b_reward,  after = "deliver_reward") 
               | a_reward.to(b_reward,  after = "deliver_reward") 
               | b_reward.to.itself() 
    )

    def __init__(self, parent):
        super(linear_track, self).__init__()
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA})
        self.parent = parent


    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.log(f"arm {arm} correct")
        self.parent.trigger_reward(arm, 'full')


    def handle_input(self, dg_input):
        if dg_input in self.beams.index:
            self.beams[dg_input]()