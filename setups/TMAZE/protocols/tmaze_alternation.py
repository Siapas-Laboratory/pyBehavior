from statemachine import StateMachine, State
from PyQt5.QtCore import pyqtSignal

import sys
sys.path.append("../")
from utils import *


class tmaze_alternation(StateMachine):

    sleep = State("sleep", initial=True)
    stem_reward= State("stem_reward")
    stem_small_reward = State("stem_small_reward")

    a_reward= State("a_reward")
    a_no_reward = State("a_no_reward")
    a_small_reward = State("a_small_reward")

    b_reward= State("b_reward")
    b_no_reward = State("b_no_reward")
    b_small_reward = State("b_small_reward")

    wandering = State("wandering")

    beamA =  ( stem_reward.to(a_reward, cond="correct_trial",  after = "deliver_reward") 
               | stem_reward.to(a_no_reward, cond="incorrect_trial") 
               | stem_small_reward.to(a_reward, cond="correct_trial",  after = "deliver_reward") 
               | stem_small_reward.to(a_no_reward, cond="incorrect_trial") 
               | b_no_reward.to(a_small_reward, cond = "correct_trial",  after = "deliver_small_reward")
               | b_reward.to(wandering) |  b_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself()
               | a_reward.to.itself() 
               | a_no_reward.to.itself() 
               | a_small_reward.to.itself()
    )


    beamB =  ( stem_reward.to(b_reward, cond="correct_trial", after = "deliver_reward") 
               | stem_reward.to(b_no_reward, cond="incorrect_trial") 
               | stem_small_reward.to(b_reward, cond="correct_trial",  after = "deliver_reward") 
               | stem_small_reward.to(b_no_reward, cond="incorrect_trial") 
               | a_no_reward.to(b_small_reward, cond = "correct_trial",  after = "deliver_small_reward")
               | a_reward.to(wandering) | a_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself() 
               | b_reward.to.itself() 
               | b_no_reward.to.itself() 
               | b_small_reward.to.itself()
    )

    beamS =  ( a_reward.to(stem_reward,  after =  "toggle_target") 
               | a_no_reward.to(stem_small_reward,  after =  "toggle_target") 
               | a_small_reward.to(stem_small_reward,  after = "toggle_target")
               | b_reward.to(stem_reward,  after = "toggle_target") 
               | b_no_reward.to(stem_small_reward,  after =  "toggle_target") 
               | b_small_reward.to(stem_small_reward,  after =  "toggle_target") 
               | wandering.to(stem_small_reward,  after =  "toggle_target") 
               | sleep.to(stem_reward,  after =  "toggle_target")
               | stem_reward.to.itself() 
               | stem_small_reward.to.itself()
    )


    def __init__(self, parent):
        super(TMAZE, self).__init__()
        self.target = None
        self.init = False
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA, 
                                'beam17': self.beamS })

        self.valves = pd.Series({'a': 'juicer_valve1', 
                                 's': 'juicer_valve2', 
                                 'b': 'juicer_valve3'})
        self.parent = parent


    def correct_trial(self, event_data):
        if self.target is None:
            self.target = event_data.target.id[0]
        return self.target == event_data.target.id[0]

    def incorrect_trial(self, event_data):
        if self.target is None:
            return False
        else:
            return self.target != event_data.target.id[0]
    
    def toggle_target(self, event_data):
        if "small" in event_data.target.id:
            self.deliver_small_reward()
        else:
            self.deliver_reward()
        if not self.init:
            self.init = True
            return
        else:
            self.target = 'b' if self.target=='a' else 'a'
            print(f"new target is {self.target}")

    def deliver_reward(self):
        print(f"triggering reward on arm {self.current_state.id[0]}")
        self.parent.trigger_reward(self.valves[self.current_state.id[0]], 'full')


    def deliver_small_reward(self):
        print(f"triggering small reward on arm {self.current_state.id[0]}")
        self.parent.trigger_reward(self.valves[self.current_state.id[0]], 'small')

    def handle_input(self, prev, current):
        change = (prev != current) & current
        change = change.loc[self.beams.index]
        if change.any():
            self.beams[change.index[change][0]]()