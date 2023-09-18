from statemachine import StateMachine
from abc import ABCMeta, abstractmethod


class ProtocolMeta(type(StateMachine), ABCMeta):
    pass

class Protocol(StateMachine, metaclass = ProtocolMeta):
    @abstractmethod
    def handle_input(self, _input):
        ...