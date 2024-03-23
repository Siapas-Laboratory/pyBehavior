from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QLabel, QCheckBox, QComboBox, QFrame
from PyQt5.QtGui import  QDoubleValidator
import time
from pyBehavior.gui import RewardWidget
from ratBerryPi.resources.pump import TriggerMode
from ratBerryPi.interfaces import RewardInterface
import typing


class PumpConfig(QFrame):

    def __init__(self, interface:RewardInterface, pump:str, modules:typing.List[str] = None):
        super(PumpConfig, self).__init__()

        self.interface = interface
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
        cur_syringe = self.interface.pumps[self.pump].syringe.syringeType
        self.syringe_select.setCurrentIndex(self.syringe_select.findText(cur_syringe))
        self.syringe_select.currentIndexChanged.connect(self.change_syringe)

        # TODO: need function on server side to change step type and step delay so i can control them step type from here
        # need a button to fill the lines

        syringe_layout.addWidget(syringe_label)
        syringe_layout.addWidget(self.syringe_select)
        vlayout.addLayout(syringe_layout)

        self.auto_fill_btn = QPushButton("Toggle Auto-Fill")
        self.auto_fill_btn.setCheckable(True)
        init_state = self.interface.auto_fill
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

        self.interface.pumps[self.pump].pos_updater.pos_updated.connect(self.update_pos)

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(1)

        vlayout.addLayout(syringe_layout)
        self.setLayout(vlayout)

    def calibrate(self):
        self.interface.calibrate(self.pump)

    def fill_lines(self):
        self.interface.fill_lines(self.modules)

    def empty_lines(self):
        self.interface.empty_lines()

    def toggle_auto_fill(self):
        self.interface.toggle_auto_fill(on = not self.interface.auto_fill)
        time.sleep(.1)
        self.auto_fill_btn.setChecked(self.interface.auto_fill)

    def change_syringe(self):
        self.interface.change_syringe(pump = self.pump, 
                                      syringeType = self.syringe_select.currentText())
        
    def push_to_res(self):
        self.interface.push_to_reservoir(pump = self.pump, amount = float(self.push_amt.text()) )

    def update_pos(self, pos):
        self.pos_label.setText(f"Position: {pos:.3f} cm")

        

class RPIRewardControl(RewardWidget):
    """
    A widget for controlling ratBerryPi reward modules locally on the pi

    ...
    PyQt Signals

    new_lick(bool)

    ...
    Methods

    reset_licks()
    update_post_delay(post_delay)
    toggle_led(on)
    toggle_valve(open_valve)
    play_tone(freq, volume, dur)
    trigger_reward(amount, force, enqueue)
    
    """

    new_lick = pyqtSignal(bool, name = "newLick")

    def __init__(self, interface:RewardInterface, module:str):

        super(RPIRewardControl, self).__init__()
        self.interface = interface
        self.module = module
    
        vlayout= QVBoxLayout()

        # module name
        module_label = QLabel(self.module)
        vlayout.addWidget(module_label)

        # pump name
        pump_name =   self.interface.modules[self.module].pump.name
        pump_label = QLabel(f"Pump: {pump_name}")
        vlayout.addWidget(pump_label)

        # widget to display and reset lick count
        lick_layout = QHBoxLayout()
        self.lick_count = QLabel(f"Lick Count: {self.interface.modules[self.module].lickometer.licks}")
        lick_layout.addWidget(self.lick_count)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_licks)
        lick_layout.addWidget(reset_btn)
        vlayout.addLayout(lick_layout)
        self.interface.modules[module].lickometer.lick_notifier.new_lick.connect(self._update_licks)

        # widget to control post reward delay
        post_delay_layout = QHBoxLayout()
        post_delay_layout.addWidget(QLabel("Post Reward Delay (s): "))
        self.post_delay = QLineEdit()
        self.post_delay.setValidator(QDoubleValidator())
        self.post_delay.setText(str(  self.interface.modules[self.module].post_delay))
        self.post_delay.editingFinished.connect(self.update_post_delay)
        post_delay_layout.addWidget(self.post_delay)
        vlayout.addLayout(post_delay_layout)

        # widget to set reward amount and manually deliver
        pulse_layout = QHBoxLayout()
        amt_label = QLabel("Reward Amount (mL)")
        self.amt = QLineEdit()
        self.amt.setValidator(QDoubleValidator())
        self.amt.setText("0.2")
        pulse_btn = QPushButton("Pulse")
        pulse_btn.clicked.connect(self._single_pulse)
        pulse_layout.addWidget(amt_label)
        pulse_layout.addWidget(self.amt)
        pulse_layout.addWidget(pulse_btn)
        vlayout.addLayout(pulse_layout)

        # widget to set small reward fraction and manually deliver
        small_pulse_layout = QHBoxLayout()
        small_pulse_edit_label = QLabel("Small Pulse Fraction")
        self.small_pulse_frac = QLineEdit()
        only_frac = QDoubleValidator(0.,1., 6, notation = QDoubleValidator.StandardNotation)
        self.small_pulse_frac.setText("0.6")
        self.small_pulse_frac.setValidator(only_frac)
        small_pulse_btn = QPushButton("Small Pulse")
        small_pulse_btn.clicked.connect(self._small_pulse)
        small_pulse_layout.addWidget(small_pulse_edit_label)
        small_pulse_layout.addWidget(self.small_pulse_frac)
        small_pulse_layout.addWidget(small_pulse_btn)
        vlayout.addLayout(small_pulse_layout)

        # widget to control speaker tone frequency
        tone_freq_layout = QHBoxLayout()
        tone_freq_label = QLabel("Tone Frequency [Hz]")
        self.tone_freq = QLineEdit()
        self.tone_freq.setValidator(QDoubleValidator())
        self.tone_freq.setText("800")
        tone_freq_layout.addWidget(tone_freq_label)
        tone_freq_layout.addWidget(self.tone_freq)
        vlayout.addLayout(tone_freq_layout)

        # widget to control speaker tone duration
        tone_dur_layout = QHBoxLayout()
        tone_dur_label = QLabel("Tone Duration [s]")
        self.tone_dur = QLineEdit()
        self.tone_dur.setValidator(QDoubleValidator())
        self.tone_dur.setText("1")
        tone_dur_layout.addWidget(tone_dur_label)
        tone_dur_layout.addWidget(self.tone_dur)
        vlayout.addLayout(tone_dur_layout)

        # widget to control speaker tone volume
        tone_vol_layout = QHBoxLayout()
        tone_vol_label = QLabel("Tone Volume")
        self.tone_vol = QLineEdit()
        self.tone_vol.setValidator(only_frac)
        self.tone_vol.setText("1")
        tone_vol_layout.addWidget(tone_vol_label)
        tone_vol_layout.addWidget(self.tone_vol)
        vlayout.addLayout(tone_vol_layout)

        # button to manually play tone
        tone_btn = QPushButton("Play Tone")
        tone_btn.clicked.connect(self.play_tone)
        vlayout.addWidget(tone_btn)
        
        # button to toggle the led
        self.led_btn = QPushButton("Toggle LED")
        self.led_btn.setCheckable(True)
        init_state =   self.interface.modules[self.module].LED.on
        self.led_btn.setChecked(init_state)
        self.led_btn.clicked.connect(self.toggle_led)
        vlayout.addWidget(self.led_btn)

        # button to toggle the valve
        self.valve_btn = QPushButton("Toggle Valve")
        self.valve_btn.setCheckable(True)
        init_state =   self.interface.modules[self.module].valve.is_open
        self.valve_btn.setChecked(init_state)
        self.valve_btn.clicked.connect(self.toggle_valve)
        vlayout.addWidget(self.valve_btn)

        # some formatting
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(2)
        self.setLayout(vlayout)

    def _update_licks(self) -> None:
        self.lick_count.setText(f"Lick Count: {self.interface.modules[self.module].lickometer.licks}")
        self.new_lick.emit(True)

    def _single_pulse(self) -> None:
        self.trigger_reward(float(self.amt.text()))

    def _small_pulse(self) -> None:
        self.trigger_reward(float(self.small_pulse_frac.text()) * float(self.amt.text()))
    
    def reset_licks(self) -> None:
        """
        reset the lick count for this module
        """

        self.interface.reset_licks(self.module)
        self.lick_count.setText(f"Lick Count: {self.interface.modules[self.module].lickometer.licks}")
    
    def update_post_delay(self, post_delay:float = None) -> None:
        """
        update the time to wait post pump actuation before closing the
        valve associated to a module

        Args:
            post_delay: float (optional)
                new post pump actuation delay in seconds
        """
        post_delay = post_delay if post_delay is not None else float(self.post_delay.text())
        self.interface.update_post_delay(module = self.module, 
                                         post_delay = float(self.post_delay.text()))
        self.post_delay.setText(f"{post_delay}")

    def play_tone(self, freq:float = None, volume:float = None, dur:float = None) -> None:
        """
        play a tone of a specified frequency volume and duration.
        by default all inputs are set according to the values set in
        the gui

        Args:
            freq: float (optional)
                tone frequency in Hz
            volume: float (optional)
                fraction of max volume to play the tone at.
                this value should be between 0 and 1
            dur: float (optional)
                duration of the tone in seconds            
        """

        freq = freq if freq is not None else float(self.tone_freq.text())
        volume = volume if volume is not None else float(self.tone_vol.text())
        dur = dur if dur is not None else float(self.tone_dur.text())

        self.interface.play_tone(
            module = self.module,
            freq = freq,
            volume = volume,
            dur = dur
        )

    def toggle_led(self, on:bool = None) -> None:
        """
        toggle the led. by default the led is toggled
        to the opposite of it's current state 
        (i.e. turned off if on and vice versa)

        Args:
            on: bool (optional)
                whether to turn the led on 
        """

        if on is None:
            led_state = self.interface.modules[self.module].LED.on
            on = not led_state
        self.interface.toggle_LED(module = self.module, on = on)
        self.led_btn.setChecked(self.interface.modules[self.module].LED.on)

    def toggle_valve(self, open_valve:bool = None):
        """
        toggle the state of the valve. by default the valve
        is toggled to the opposite of its current state
        (i.e. opened if closed and vice versa)

        Args:
            open_valve: bool (optional)
                whether to open the valve
        """

        if open_valve is None:
            valve_state = self.interface.modules[self.module].valve.is_open
            open_valve = not valve_state
        self.interface.toggle_valve(module = self.module, open_valve = open_valve)
        self.valve_btn.setChecked(self.interface.modules[self.module].valve.is_open)


    def trigger_reward(self, amount:float, force:bool = True, enqueue:bool = False) -> None:
        """
        trigger a reward of a specified amount

        Args: 
            amount: float
                amount of reward to deliver in mL
            force: bool (optional)
                whether or not to override a currently
                running reward thread associated with this
                module's pump in order to deliver this reward
            enqueue: bool (optional)
                if there is currently a reward thread running
                that is using this module's pump, when set to True,
                this argument allows the user to enqueue this reward 
                delivery until after the currently running task is finished
        """

        self.interface.trigger_reward(
            module = self.module,
            amount = amount,
            force = force,
            enqueue = enqueue
        )