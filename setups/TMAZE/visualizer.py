import logging
import sys
from PyQt5.QtWidgets import  QSpacerItem, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy, QGridLayout
sys.path.append("../")
from utils import *



class TMAZE(SetupVis):

    def __init__(self):
        super(TMAZE, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()

    def buildUI(self):
        beam_ports = self.mapping.loc[self.mapping.index.str.contains("beam")]
        self.beams = beam_ports.rename('port').to_frame()

        self.beams['state'] = np.zeros((len(beam_ports),), dtype = bool)
        right_arm = [f'beam{i}' for i in range(1,9)]
        left_arm = [f'beam{i}' for i in range(9,17)]
        bottom_arm = [f'beam{i}' for i in range(17,28)]
        sleep_arm = ['beam29', 'beam28']

        self.beams.loc[right_arm, 'arm'] = "right"
        self.beams.loc[left_arm, 'arm'] = "left"
        self.beams.loc[bottom_arm, 'arm'] = "bottom"
        self.beams.loc[sleep_arm, 'arm'] = "sleep"

        # self.beam_thread = DIChanThread(beam_ports)
        # self.beam_thread.state_updated.connect(self.register_state_change)
        vlayout = QVBoxLayout()
        stem_valve = ValveControl(self.mapping.loc['juicer_valve2'], 'juicer_valve2')
        vlayout.addWidget(stem_valve)
        hlayout = QHBoxLayout()
        b_valve = ValveControl(self.mapping.loc['juicer_valve3'], 'juicer_valve3')
        hlayout.addWidget(b_valve)
        grid = QGridLayout()
        beam_buttons = {}
        for i, beam in enumerate(bottom_arm):
            btn = QPushButton(beam)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 1em;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            grid.addWidget(btn, i, 8)
            beam_buttons.update({beam: btn})

        for i,beam in enumerate(right_arm[::-1] + [''] + left_arm):
            if beam == '':
                continue
            btn = QPushButton(beam)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 1em;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            grid.addWidget(btn, 10, i)
            beam_buttons.update({beam: btn})
        
        for beam in sleep_arm:
            btn = QPushButton(beam)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet("""
            QPushButton {
                border-radius : 1em;  
                border : 2px solid black 
            }
            QPushButton::checked { 
                background-color : red;
            }
            """
            )
            btn.setCheckable(True)
            grid.addWidget(btn, 11+i, 8)
            beam_buttons.update({beam: btn})
        
    
        self.beams['button'] = pd.Series(beam_buttons)
        hlayout.addLayout(grid)
        a_valve = ValveControl(self.mapping.loc['juicer_valve1'], 'juicer_valve1')
        hlayout.addWidget(a_valve)
        vlayout.addLayout(hlayout)
        # self.beam_thread.start()
        self.layout.addLayout(vlayout)

    def trigger_reward(self, port, typ = 'full'):
        # get the appropriate pulse duration for this port
        print(f"pulsing port {port}, {typ}")

    def register_state_change(self, data):
        if self.running:
            self.state_machine.handle_input(self.beams.state, data)
        prev = self.beams.state
        changed = data[self.beams.state != data].index
        for c in changed:
            self.beams.loc[c,'button'].toggle()
        self.beams['state'] = data
        logging.debug(prev)
        logging.debug(data)
    