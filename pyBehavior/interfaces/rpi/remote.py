from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QLabel, QCheckBox, QComboBox, QFrame
from PyQt5.QtGui import  QDoubleValidator
import time
from pyBehavior.gui import RewardWidget


class PumpConfig(QFrame):

    def __init__(self, client, pump, modules = None):
        super(PumpConfig, self).__init__()
        self.client = client
        self.pump = pump
        self.modules = modules

        vlayout = QVBoxLayout()
        pump_label = QLabel(self.pump)
        vlayout.addWidget(pump_label)

        self.pos_label = QLabel("Position: ")
        vlayout.addWidget(self.pos_label)

        syringe_layout = QHBoxLayout()
        syringe_label = QLabel("Syringe Type:")
        self.syringe_select = QComboBox()
        self.syringe_select.addItems(["BD5mL", "BD10mL", "BD30mL"])
        cur_syringe = self.client.get(f"pumps['{self.pump}'].syringe.syringeType")
        self.syringe_select.setCurrentIndex(self.syringe_select.findText(cur_syringe))
        self.syringe_select.currentIndexChanged.connect(self.change_syringe)

        # TODO: need function on server side to change step type and step delay so i can control them step type from here
        # need a button to fill the lines

        syringe_layout.addWidget(syringe_label)
        syringe_layout.addWidget(self.syringe_select)
        vlayout.addLayout(syringe_layout)

        self.auto_fill_btn = QPushButton("Toggle Auto-Fill")
        self.auto_fill_btn.setCheckable(True)
        init_state = bool(self.client.get(f"auto_fill"))
        self.auto_fill_btn.setChecked(init_state)
        self.auto_fill_btn.clicked.connect(self.toggle_auto_fill)
        vlayout.addWidget(self.auto_fill_btn)

        self.fill_btn = QPushButton("Fill Lines")
        self.fill_btn.clicked.connect(self.fill_lines)
        vlayout.addWidget(self.fill_btn)

        #TODO: add a fill all lines button

        push_res_label = QLabel("Push To Reservoir")
        vlayout.addWidget(push_res_label)
        push_res_layout = QHBoxLayout()
        amt_label = QLabel("Amount")
        self.push_amt = QLineEdit()
        self.push_amt.setValidator(QDoubleValidator())
        self.push_amt.setText("2")
        self.push_res_btn = QPushButton("Push")
        self.push_res_btn.clicked.connect(self.push_to_res)
        push_res_layout.addWidget(amt_label)
        push_res_layout.addWidget(self.push_amt)
        push_res_layout.addWidget(self.push_res_btn)
        vlayout.addLayout(push_res_layout)

        self.empty_btn = QPushButton("Empty Lines")
        self.empty_btn.clicked.connect(self.empty_lines)
        vlayout.addWidget(self.empty_btn)


        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.calibrate)
        vlayout.addWidget(self.calibrate_btn)

        self.pos_thread = PumpConfig.RPIPumpPosThread(self.client, self.pump)
        self.pos_thread.pos_updated.connect(self.update_pos)
        self.pos_thread.start()

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(1)

        vlayout.addLayout(syringe_layout)
        self.setLayout(vlayout)

    def calibrate(self):
        self.client.run_command('calibrate', {'pump': self.pump}, channel = 'run')


    def fill_lines(self):
        self.client.run_command('fill_lines', {'modules': self.modules}, channel = 'run')

    def empty_lines(self):
        self.client.run_command('empty_lines', {}, channel = 'run')

    def toggle_auto_fill(self):
        args = {
            'on': not bool(self.client.get(f"auto_fill"))
        }
        self.client.run_command('toggle_auto_fill', args, channel = 'run')
        time.sleep(.1)
        self.auto_fill_btn.setChecked(bool(self.client.get(f"auto_fill")))

    def change_syringe(self):
        args = {
            'pump': self.pump,
            'syringeType': self.syringe_select.currentText()
        }
        self.client.run_command('change_syringe', args, channel = 'run')

    def push_to_res(self):
        args = {
            'pump': self.pump,
            'amount': float(self.push_amt.text())
        }
        self.client.run_command('push_to_reservoir', args, channel = 'run')

    def update_pos(self, pos):
        self.pos_label.setText(f"Position: {pos:.3f} cm")
        
    class RPIPumpPosThread(QThread):
        pos_updated = pyqtSignal(object)
        def __init__(self, client, pump):
            super(PumpConfig.RPIPumpPosThread, self).__init__()
            self.client = client
            self.pump = pump
            self.client.new_channel(self.pump)
            self.pos = None

        def run(self):
            while True:
                try:
                    pos = self.client.get(f"pumps['{self.pump}'].position", channel = self.pump)
                    if pos != self.pos:
                        self.pos = pos
                        self.pos_updated.emit(self.pos)
                except ValueError as e:
                    print(f"invalid position read on '{self.pump}'")
                finally:
                    time.sleep(.1)
        

class RPIRewardControl(RewardWidget):

    new_licks = pyqtSignal(int)

    def __init__(self, client, module):
        super(RPIRewardControl, self).__init__()

        self.module = module
        self.client = client
    
        vlayout= QVBoxLayout()

        valve_label = QLabel(self.module)
        vlayout.addWidget(valve_label)

        pump_name = self.client.get(f"modules['{self.module}'].pump.name")
        pump_label = QLabel(f"Pump: {pump_name}")
        vlayout.addWidget(pump_label)

        lick_layout = QHBoxLayout()
        self.lick_count_n = int(self.client.get(f"modules['{self.module}'].lickometer.licks"))
        self.lick_count = QLabel(f"Lick Count: {self.lick_count_n}")
        lick_layout.addWidget(self.lick_count)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_licks)
        lick_layout.addWidget(reset_btn)
        vlayout.addLayout(lick_layout)
        self.lick_thread = RPIRewardControl.RPILickThread(self.client, self.module)
        self.lick_thread.lick_num_updated.connect(self.update_licks)
        self.lick_thread.start()

        post_delay_layout = QHBoxLayout()
        post_delay_layout.addWidget(QLabel("Post Reward Delay (s): "))
        self.post_delay = QLineEdit()
        self.post_delay.setValidator(QDoubleValidator())
        self.post_delay.setText(str(self.client.get(f"modules['{self.module}'].post_delay")))
        self.post_delay.editingFinished.connect(self.update_post_delay)
        post_delay_layout.addWidget(self.post_delay)
        vlayout.addLayout(post_delay_layout)


        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(QLabel("Trigger Mode:"))
        self.trigger_mode = QComboBox()
        self.trigger_mode.addItems(["No Trigger", "Single Trigger", "Continuous Trigger"])
        self.trigger_mode_opts = ["NO_TRIGGER", "SINGLE_TRIGGER", "CONTINUOUS_TRIGGER"]
        self.trigger_mode.setCurrentIndex(0)
        trigger_layout.addWidget(self.trigger_mode)
        vlayout.addLayout(trigger_layout)

        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Reward Lick Threshold: "))
        self.reward_thresh = QLineEdit()
        self.reward_thresh.setValidator(QDoubleValidator())
        self.reward_thresh.setText(str(float(self.client.get(f"modules['{self.module}'].reward_thresh"))))
        self.reward_thresh.editingFinished.connect(self.update_reward_thresh)
        thresh_layout.addWidget(self.reward_thresh)
        vlayout.addLayout(thresh_layout)

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
        init_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
        self.led_btn.setChecked(init_state)
        self.led_btn.clicked.connect(self.toggle_led)
        vlayout.addWidget(self.led_btn)

        self.valve_btn = QPushButton("Toggle Valve")
        self.valve_btn.setCheckable(True)
        init_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
        self.valve_btn.setChecked(init_state)
        self.valve_btn.clicked.connect(self.toggle_valve)
        vlayout.addWidget(self.valve_btn)

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(2)

        self.setLayout(vlayout)
    
    def update_licks(self, amt):
        if amt > 0: self.new_licks.emit(amt)
        self.lick_count_n += amt
        self.lick_count.setText(f"Lick Count: {self.lick_count_n}")

    def reset_licks(self):
        self.client.run_command("reset_licks", {'module': self.module}, channel = "run")

    def update_reward_thresh(self):
        self.client.run_command("set_reward_thresh",
                                args = {
                                    "module": self.module,
                                    "val": int(self.reward_thresh.text())
                                }, channel = 'run')
    
    def update_post_delay(self):
        args = {'module': self.module,
                'post_delay': float(self.post_delay.text())}
        self.client.run_command('update_post_delay', args, channel = 'run')

    def play_tone(self):
        freq = float(self.tone_freq.text())
        vol = float(self.tone_vol.text())
        dur = float(self.tone_dur.text())

        args = {'module': self.module,
                'freq': freq,
                'dur': dur,
                'volume': vol}
        
        status = self.client.run_command('play_tone', args, channel = 'run')

        if not status=='SUCCESS\n':
            print('error status', status)

    def toggle_led(self):
        led_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
        args = {'module': self.module,
                'on': not led_state}
        status = self.client.run_command('toggle_LED', args, channel = 'run')
        if not status=='SUCCESS\n':
            led_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
            self.led_btn.setChecked(led_state)
            print('error status', status)

    def toggle_valve(self):
        valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
        args = {'module': self.module,
                'open_valve': not valve_state}
        status = self.client.run_command('toggle_valve', args, channel = 'run')
        if not status=='SUCCESS\n':
            valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
            self.valve_btn.setChecked(valve_state)
            print('error status', status)

    def single_pulse(self):
        self.pulse(float(self.amt.text()))

    def small_pulse(self):
        self.pulse(float(self.small_pulse_frac.text()) * float(self.amt.text()))
        
    def pulse(self, amount, force = True, wait = False):
        args = {'module': self.module, 
                'amount': amount,
                'trigger_mode': self.trigger_mode_opts[self.trigger_mode.currentIndex()],
                'force': force,
                'wait' : wait}
        status = self.client.run_command("trigger_reward", args, channel = 'run')
        if not status=='SUCCESS\n':
            print('error status', status)

    def trigger_reward(self, small = False, force = True, wait = False):
        if small:
            amount =  float(self.small_pulse_frac.text()) * float(self.amt.text())
        else:
            amount =  float(self.amt.text())
        self.pulse(amount, force = force, wait = wait)


    class RPILickThread(QThread):
        lick_num_updated = pyqtSignal(int)
        def __init__(self, client, module):
            super(RPIRewardControl.RPILickThread, self).__init__()
            self.client = client
            self.module = module
            self.client.new_channel(f"{self.module}_licks")
        
        def run(self):
            prev_licks = int(self.client.get(f"modules['{self.module}'].lickometer.licks",
                                                channel = f"{self.module}_licks"))
            while True:
                try:
                    licks = int(self.client.get(f"modules['{self.module}'].lickometer.licks",
                                                channel = f"{self.module}_licks"))
                    if licks!=prev_licks:
                        self.lick_num_updated.emit(licks - prev_licks)
                        prev_licks = licks
                except ValueError as e:
                    print(f"invalid read on '{self.module}'")
                    raise e
                finally:
                    time.sleep(.005)