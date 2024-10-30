from statemachine import StateMachine
from abc import ABCMeta, abstractmethod
from datetime import datetime
import threading
import time

class ProtocolMeta(type(StateMachine), ABCMeta):
    pass

class Protocol(StateMachine, metaclass = ProtocolMeta):
    """
    
    
    """
    def __init__(self, parent):
        super(Protocol, self).__init__()
        self.parent = parent
        self._has_timeout = hasattr(self, 'timeout')
        if self._has_timeout:
            self._timeout_thread = None
            self._in_timeout = False
            self._timeout_event = threading.Event()
            self._call_timeout_thread = threading.Thread(target=self._call_timeout)
            self._call_timeout_thread.start()
        
    @abstractmethod
    def handle_input(self, _input):
        ...

    def _call_timeout(self):
        while not self.parent._running:
            time.sleep(0.5)
        while self.parent._running:
            if self._timeout_event.is_set():
                self._timeout_event.clear()
                self.timeout()
            time.sleep(.5)

    def start_countdown(self, timeout):
        assert self._has_timeout, "this protocol is missing a timeout action. cannot use the start_countdown method"
        def countdown():
            start = datetime.now()
            offset = 0
            elapsed = 0
            while (elapsed < timeout) and self._in_timeout:
                time.sleep(0.1)
                if self.parent._paused:
                    offset = elapsed
                    start = datetime.now()
                else:
                    elapsed = offset + (datetime.now() - start).total_seconds()
            if self._in_timeout:
                self._in_timeout = False
                self._timeout_event.set()

        self.stop_countdown()
        self._in_timeout = True
        self._timeout_thread = threading.Thread(target = countdown)
        self._timeout_thread.start()

    def stop_countdown(self):
        if self._has_timeout:
            self._in_timeout = False
            if self._timeout_thread is not None:
                self._timeout_thread.join()