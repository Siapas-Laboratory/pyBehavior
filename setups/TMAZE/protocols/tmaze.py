from statemachine import StateMachine, State
sys.path.append("../")
from utils import *


class TMAZE(StateMachine):

    sleep = State("sleep", initial=True)
    stem_reward= State("stem_reward", enter = "toggle_target")
    stem_small_reward = State("stem_small_reward", enter = "toggle_target")

    a_reward= State("a_reward", enter = "deliver_reward")
    a_no_reward = State("a_no_reward")
    a_small_reward = State("a_small_reward", enter = "deliver_small_reward")

    b_reward= State("b_reward", enter = "deliver_reward")
    b_no_reward = State("b_no_reward")
    b_small_reward = State("b_small_reward", enter = "deliver_small_reward")

    wandering = State("wandering")

    beamA =  ( stem_reward.to(a_reward, cond="correct_trial") 
               | stem_reward.to(a_no_reward, cond="incorrect_trial") 
               | stem_small_reward.to(a_reward, cond="correct_trial") 
               | stem_small_reward.to(a_no_reward, cond="incorrect_trial") 
               | b_no_reward.to(a_small_reward, cond = "correct_trial")
               | b_reward.to(wandering) |  b_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself()
               | a_reward.to.itself() | a_no_reward.to.itself() 
               | a_small_reward.to.itself()
    )

    beamB =  ( stem_reward.to(b_reward, cond="correct_trial") 
               | stem_reward.to(b_no_reward, cond="incorrect_trial") 
               | stem_small_reward.to(b_reward, cond="correct_trial") 
               | stem_small_reward.to(b_no_reward, cond="incorrect_trial") 
               | a_no_reward.to(b_small_reward, cond = "correct_trial")
               | a_reward.to(wandering) | a_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself()
               | b_reward.to.itself() | b_no_reward.to.itself() 
               | b_small_reward.to.itself()
    )

    beamS =  ( a_reward.to(stem_reward) | a_no_reward.to(stem_small_reward) 
               | a_small_reward.to(stem_small_reward)
               | b_reward.to(stem_reward) | b_no_reward.to(stem_small_reward) 
               | b_small_reward.to(stem_small_reward) 
               | wandering.to(stem_small_reward) | sleep.to(stem_reward)
               | stem_reward.to.itself() | stem_small_reward.to.itself()
    )

    def __init__(self):
        super(TMAZE, self).__init__()
        self.target = None
        self.init = False
        self.beams = pd.Series({'beam9': self.beamA, 
                                'beam16': self.beamB, 
                                'beam17': self.beamS })


    def correct_trial(self, event_data):
        if self.target is None:
            self.target = event_data.target.id[0]
        return self.target == event_data.target.id[0]

    def incorrect_trial(self, event_data):
        if self.target is None:
            return False
        else:
            return self.target != event_data.target.id[0]
    
    def toggle_target(self):
        # need to check state and trigger appropriate reward
        if not self.init:
            self.init = True
            return
        else:
            self.target = 'b' if self.target=='a' else 'a'

    def deliver_reward(self):
        print("delivering reward to valve x")
        pass

    def deliver_small_reward(self):
        print("delivering small reward to valve x")
        pass

    def handle_input(self, prev, current):
        change = prev != current
        change = change.loc[self.beams.index]
        if change.any():
            self.beams[change.index[change][0]]()
