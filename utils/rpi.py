from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QLabel, QCheckBox
from PyQt5.QtGui import  QDoubleValidator

path_to_rpi_reward_mod = '/Users/nathanielnyema/Downloads/rpi-reward-module/'
# path_to_rpi_reward_mod = r'C:\Users\Siapas\Downloads\rpi-reward-module'

class RPIRewardControl(QWidget):

    def __init__(self, client, module):
        super(RPIRewardControl, self).__init__()

        self.module = module
        self.client = client
        self.name = module

        if not self.client.connected:
            self.client.connect()
        
        vlayout= QVBoxLayout()
        valve_label = QLabel(self.name)
        vlayout.addWidget(valve_label)

        #NEED control of syringe type
        self.lick_triggered = QCheckBox('Lick Triggered')
        vlayout.addWidget(self.lick_triggered)
        self.lick_triggered.setChecked(False)

        pulse_layout = QHBoxLayout()
        amt_label = QLabel("Reward Amount (mL)")
        self.amt = QLineEdit()
        self.amt.setValidator(QDoubleValidator())
        self.amt.setText("0.2")

        pulse_btn = QPushButton("Pulse")
        pulse_btn.clicked.connect(self.single_pulse)
        pulse_layout.addWidget(amt_label)
        pulse_layout.addWidget(self.amt)
        pulse_layout.addWidget(pulse_btn)
        vlayout.addLayout(pulse_layout)

        small_pulse_layout = QHBoxLayout()
        small_pulse_edit_label = QLabel("Small Pulse Fraction")
        self.small_pulse_frac = QLineEdit()
        only_frac = QDoubleValidator(0.,1., 6, notation = QDoubleValidator.StandardNotation)
        self.small_pulse_frac.setText("0.6")
        self.small_pulse_frac.setValidator(only_frac) # this doesn't seem to be working for some reason
        small_pulse_btn = QPushButton("Small Pulse")
        small_pulse_btn.clicked.connect(self.small_pulse)
        small_pulse_layout.addWidget(small_pulse_edit_label)
        small_pulse_layout.addWidget(self.small_pulse_frac)
        small_pulse_layout.addWidget(small_pulse_btn)
        vlayout.addLayout(small_pulse_layout)

        tone_freq_layout = QHBoxLayout()
        tone_freq_label = QLabel("Tone Frequency [Hz]")
        self.tone_freq = QLineEdit()
        self.tone_freq.setValidator(QDoubleValidator())
        self.tone_freq.setText("800")
        tone_freq_layout.addWidget(tone_freq_label)
        tone_freq_layout.addWidget(self.tone_freq)
        vlayout.addLayout(tone_freq_layout)

        tone_dur_layout = QHBoxLayout()
        tone_dur_label = QLabel("Tone Duration [s]")
        self.tone_dur = QLineEdit()
        self.tone_dur.setValidator(QDoubleValidator())
        self.tone_dur.setText("1")
        tone_dur_layout.addWidget(tone_dur_label)
        tone_dur_layout.addWidget(self.tone_dur)
        vlayout.addLayout(tone_dur_layout)

        tone_vol_layout = QHBoxLayout()
        tone_vol_label = QLabel("Tone Volume")
        self.tone_vol = QLineEdit()
        self.tone_vol.setValidator(only_frac)
        self.tone_vol.setText("1")
        tone_vol_layout.addWidget(tone_vol_label)
        tone_vol_layout.addWidget(self.tone_vol)
        vlayout.addLayout(tone_vol_layout)

        tone_btn = QPushButton("Play Tone")
        tone_btn.clicked.connect(self.play_tone)
        vlayout.addWidget(tone_btn)
        
        self.led_btn = QPushButton("Toggle LED")
        self.led_btn.setCheckable(True)
        req = {'module': self.module,
               'plugin': 'LED',
               'prop': 'on'}
        init_state = bool(self.client.get(req))
        self.led_btn.setChecked(init_state)
        self.led_btn.clicked.connect(self.toggle_led)
        vlayout.addWidget(self.led_btn)

        self.setLayout(vlayout)


    def play_tone(self):
        freq = float(self.tone_freq.text())
        vol = float(self.tone_vol.text())
        dur = float(self.tone_dur.text())

        args = {'module': self.module,
                'freq': freq,
                'dur': dur,
                'volume': vol}
        
        status = int(self.client.run_command('toggle_LED', args))

        if not status==1:
            print('error status', status)

    def toggle_led(self):
        req = {'module': self.module,
               'plugin': 'LED',
               'prop': 'on'}
        led_state = bool(self.client.get(req))
        args = {'module': self.module,
                'on': ~led_state}
        status = int(self.client.run_command('toggle_LED', args))
        if status != 1:
            led_state = bool(self.client.get(req))
            self.led_btn.setChecked(led_state)
            print('error status', status)

    def single_pulse(self):
        self.pulse(float(self.amt.text()))

    def small_pulse(self):
        self.pulse(float(self.small_pulse_frac.text()) * float(self.amt.text()))
        
    def pulse(self, amount):
        args = {'module': self.module, 
                'amount': amount,
                'lick_triggered': False}
        status = int(self.client.run_command("trigger_reward", args))
        if status != 1: 
            print('error status', status)

    def trigger_reward(self, small = False):
        if small:
            amount =  float(self.small_pulse_frac.text()) * float(self.amt.text())
        else:
            amount =  float(self.amt.text())
        args = {'module': self.module, 
                'amount': amount,
                'lick_triggered': self.lick_triggered.checkState()}
        status = int(self.client.run_command("trigger_reward", args))
        if status!=1:
            print('error status', status)


class RPILickThread(QThread):
    state_updated = pyqtSignal(object)
    def __init__(self, client, module):
        super(RPILickThread, self).__init__()
        assert client.connected
        self.client = client
        self.module = module
        print(self.module)
    
    def run(self):
        prev_licks = 0
        while True:
            try:
                req = {'module': self.module,
                       'plugin': 'lickometer',
                       'prop': 'licks'}
                licks = int(self.client.get(req))
                if licks!=prev_licks:
                    prev_licks = licks
                    self.state_updated.emit(licks)
            except ValueError as e:
                print(f"invalid read on {self.module}")
                raise e
