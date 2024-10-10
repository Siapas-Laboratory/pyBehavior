from pyBehavior.protocols import Protocol
from statemachine import State

REWARD_AMOUNT = 0.5
TIMEOUT_PERIOD = 5

class lick_for_reward(Protocol):
    
    not_licking = State(initial=True)
    licking = State(enter='start_nolick_countdown')

    lick = (licking.to.itself() |
            not_licking.to(licking, before='reward'))
    timeout = licking.to(not_licking)

    def reward(self):
        self.parent.trigger_reward('module1', REWARD_AMOUNT, force = False, enqueue = True)

    def start_nolick_countdown(self):
        self.start_countdown(TIMEOUT_PERIOD)
    
    def handle_input(self, data):
        if data['type'] == 'lick':
            self.lick()
