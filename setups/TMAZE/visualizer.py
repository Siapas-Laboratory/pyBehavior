import logging
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import  QSpacerItem, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy, QGridLayout
sys.path.append("../")
from utils import *



class TMAZE(SetupVis):

    def __init__(self):
        super(TMAZE, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()

    def buildUI(self):

        right_arm = [f'beam{i}' for i in range(1,9)]
        left_arm = [f'beam{i}' for i in range(9,17)]
        bottom_arm = [f'beam{i}' for i in range(17,28)]
        sleep_arm = ['beam29', 'beam28']
        all_beams = right_arm + left_arm + bottom_arm + sleep_arm
        self.beams = self.mapping.loc[all_beams].rename("port").to_frame()
        self.beams['state'] = np.zeros((len(self.beams),), dtype = bool)

        self.beams.loc[right_arm, 'arm'] = "right"
        self.beams.loc[left_arm, 'arm'] = "left"
        self.beams.loc[bottom_arm, 'arm'] = "bottom"
        self.beams.loc[sleep_arm, 'arm'] = "sleep"

        self.beam_thread = DIChanThread(self.beams.port)
        self.beam_thread.state_updated.connect(self.register_beam_break)
        vlayout = QVBoxLayout()
        self.stem_valve = ValveControl(self, self.mapping.loc['juicer_valve2'], 
                                        'juicer_valve2', 
                                        self.mapping.loc['juicer_purge'],
                                        self.mapping.loc['juicer_flush'],
                                        self.mapping.loc['juicer_bleed1'],
                                        self.mapping.loc['juicer_bleed2'])
        vlayout.addWidget(self.stem_valve)
        hlayout = QHBoxLayout()
        self.b_valve = ValveControl(self, self.mapping.loc['juicer_valve3'], 
                                    'juicer_valve3',
                                    self.mapping.loc['juicer_purge'],
                                    self.mapping.loc['juicer_flush'],
                                    self.mapping.loc['juicer_bleed1'],
                                    self.mapping.loc['juicer_bleed2'])
        hlayout.addWidget(self.b_valve)
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
        self.a_valve = ValveControl(self, self.mapping.loc['juicer_valve1'], 
                                    'juicer_valve1',
                                    self.mapping.loc['juicer_purge'],
                                    self.mapping.loc['juicer_flush'],
                                    self.mapping.loc['juicer_bleed1'],
                                    self.mapping.loc['juicer_bleed2'])
        hlayout.addWidget(self.a_valve)
        vlayout.addLayout(hlayout)
        self.buffer = {}
        self.beam_thread.start()
        self.layout.addLayout(vlayout)
        self.valves = {'a': self.a_valve, 'b': self.b_valve, 's': self.stem_valve}
        self.lick_thread = DIChanThread(self.mapping.loc[["licks_all"]], falling_edge = False)
        self.lick_thread.state_updated.connect(self.register_lick)
        self.lick_thread.start()

    def trigger_reward(self, valve, typ = 'full'):
        if typ =='full':
            self.valves[valve].pulse()
        if typ == 'small':
            self.valves[valve].small_pulse()

    def register_lick(self, data):
        self.log('lick')

    
    def register_beam_break(self, data):
        changed = data[self.beams.state != data].index
        for c in changed:
            if data.loc[c] > self.beams.loc[c].state:
                self.log(c)
                if self.running:
                    self.state_machine.handle_input(c)
            self.beams.loc[c,'button'].toggle()
        self.beams['state'] = data

    