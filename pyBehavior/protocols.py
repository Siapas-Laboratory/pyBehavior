from statemachine import StateMachine
from abc import ABCMeta, abstractmethod


class ProtocolMeta(type(StateMachine), ABCMeta):
    pass

class Protocol(StateMachine, metaclass = ProtocolMeta):
    """
    
    
    """
    def __init__(self, parent):
        super(Protocol, self).__init__()
        self.parent = parent 
        
    @abstractmethod
    def handle_input(self, _input):
        ...