from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QComboBox, QFrame
from PyQt5.QtGui import  QDoubleValidator
import time
from pyBehavior.gui import RewardWidget
import typing


class PumpConfig(QFrame):
    """
    a widget for controlling a pump on the ratBerryPi remotely
    through a client

    ...
    Methods
    
    calibrate()
    fill_lines(modules, fill_all)
    empty_lines()
    toggle_auto_fill(on)
    change_syringe(syringe_type)
    push_to_res(amount)

    """
    def __init__(self, client, pump, modules = None):
        super(PumpConfig, self).__init__()
        self.client = client
        self.pump = pump
        self.modules = modules

        vlayout = QVBoxLayout()

        # pump name
        pump_label = QLabel(self.pump)
        vlayout.addWidget(pump_label)

        # label to keep track of the pump piston position
        self.pos_label = QLabel("Position: ")
        vlayout.addWidget(self.pos_label)
        self.pos_thread = PumpConfig.RPIPumpPosThread(self.client, self.pump)
        self.pos_thread.pos_updated.connect(self._update_pos)
        self.pos_thread.start()

        # widget to select syringe
        syringe_layout = QHBoxLayout()
        syringe_label = QLabel("Syringe Type:")
        self.syringe_select = QComboBox()
        self.syringe_select.addItems(["BD1mL", "BD3mL", "BD5mL", "BD10mL", "BD30mL"])
        cur_syringe = self.client.get(f"pumps['{self.pump}'].syringe.syringeType")
        self.syringe_select.setCurrentIndex(self.syringe_select.findText(cur_syringe))
        self.syringe_select.currentIndexChanged.connect(self.change_syringe)
        syringe_layout.addWidget(syringe_label)
        syringe_layout.addWidget(self.syringe_select)
        vlayout.addLayout(syringe_layout)

        # TODO: need function on server side to change step type and step delay so i can control them from here\

        # widget to control auto-fill
        auto_fill_layout = QHBoxLayout()
        auto_fill_thresh_label = QLabel("Auto Fill Threshold Fraction: ")
        self.auto_fill_thresh = QLineEdit()
        self.auto_fill_thresh.setText(f"{self.client.get('auto_fill_frac_thresh')}")
        self.auto_fill_thresh.setValidator(QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation))
        self.auto_fill_thresh.textChanged.connect(self.set_auto_fill_frac_thresh)
        self.auto_fill_btn = QPushButton("Toggle Auto-Fill")
        self.auto_fill_btn.setCheckable(True)
        init_state = bool(self.client.get(f"auto_fill"))
        self.auto_fill_btn.setChecked(init_state)
        self.auto_fill_btn.clicked.connect(self.toggle_auto_fill)
        auto_fill_layout.addWidget(auto_fill_thresh_label)
        auto_fill_layout.addWidget(self.auto_fill_thresh)
        auto_fill_layout.addWidget(self.auto_fill_btn)
        vlayout.addLayout(auto_fill_layout)

        # button to fill the lines
        self.fill_btn = QPushButton("Fill Lines")
        self.fill_btn.clicked.connect(lambda x: self.fill_lines())
        vlayout.addWidget(self.fill_btn)

        # button to fill all the lines
        self.fill_all_btn = QPushButton("Fill all lines")
        self.fill_all_btn.clicked.connect(lambda x: self.fill_lines(fill_all = True))
        vlayout.addWidget(self.fill_all_btn)

        # widget to push some fluid to the reservoir
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

        # button to empty all of the lines
        self.empty_btn = QPushButton("Empty Lines")
        self.empty_btn.clicked.connect(self.empty_lines)
        vlayout.addWidget(self.empty_btn)

        # button to calibrate the pump
        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.calibrate)
        vlayout.addWidget(self.calibrate_btn)

        # some formatting
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(1)
        vlayout.addLayout(syringe_layout)
        self.setLayout(vlayout)

    def _update_pos(self, pos:float) -> None:
        self.pos_label.setText(f"Position: {pos:.3f} cm")

    def calibrate(self) -> None:
        """
        set pump position to 0
        """
        self.client.run_command('calibrate', {'pump': self.pump}, channel = 'run')

    def fill_lines(self, modules:typing.List[str] = None, fill_all:bool = False) -> None:
        """
        fill all of the lines leading to the modules
        this call is blocking currently so the gui will freeze

        TODO: neeed to handle the freezing more gracefully
        maybe a little loading window?

        Args:
            modules: typing.List[str] (optional)
                list of modules to fill lines for
                default behavior is to fill lines
                for all modules associated to this pump widget
        """

        if fill_all:
            modules = None
        elif modules is None:
            modules = self.modules

        self.client.run_command('fill_lines', {'modules': modules}, channel = 'run')

    def empty_lines(self) -> None:
        """
        empty all of the lines leading to the modules
        NOTE: this can only work by emptying all lines 
        for all modules associated to the pump on the 
        ratBerryPi side

        TODO: neeed to handle the freezing more gracefully
        maybe a little loading window?
        """

        self.client.run_command('empty_lines', {}, channel = 'run')

    def toggle_auto_fill(self, on:bool = None) -> None:
        """
        toggle whether or not the pumps on the reward interface
        are in auto-fill mode (i.e. they refill the syringes

        Args:
            on: bool (optional)
                whether to turn on auto-fill
                default behavior is to toggle to 
                the opposite of the current state
        """

        on = on if on is not None else not bool(self.client.get(f"auto_fill"))
        self.client.run_command('toggle_auto_fill', {'on': on}, channel = 'run')
        time.sleep(.1)
        self.auto_fill_btn.setChecked(bool(self.client.get(f"auto_fill")))

    def set_auto_fill_frac_thresh(self, value:float = None) -> None:
        """
        set the threshold fraction of the syringe volume
        at which to trigger a refill

        Args:
            value: float (optional)
                new threshold value
        """
        
        value = value if value is not None else float(self.auto_fill_thresh.text())
        self.client.run_command('set_auto_fill_frac_thresh', {'value': value}, channel = 'run')
        self.auto_fill_thresh.setText(f"{value}")

    def change_syringe(self, syringe_type:str = None) -> None:
        """
        change the syringe type

        Args:
            syringe_type: str (optional)
                new syringe type. must be a syringe in the list of syringe types
                default behavior is to use the currently selected syringe type
        """

        syringe_type = syringe_type if syringe_type is not None else self.syringe_select.currentText()
        idx = self.syringe_select.findText(syringe_type)
        if idx == -1:
            raise ValueError('Invalid syringe type specified')
        
        args = {
            'pump': self.pump,
            'syringeType': syringe_type
        }
        self.client.run_command('change_syringe', args, channel = 'run')
        self.syringe_select.setCurrentIndex(idx)

    def push_to_res(self, amount:float = None) -> None:
        """
        push a specified amount of fluid to the reservoir

        Args:
            amount: float (optional)
                amount of fluid to push in mL
                default behavior is to use the value set in
                the gui
        """

        amount = amount if amount is not None else float(self.push_amt.text())
        args = {
            'pump': self.pump,
            'amount': amount
        }
        self.client.run_command('push_to_reservoir', args, channel = 'run')
        
    class RPIPumpPosThread(QThread):
        """
        thread to keep track of pump piston position

        ...
        PyQt Signals

        pos_updated(float)
        """
        pos_updated = pyqtSignal(float)
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
    """
    A widget for controlling ratBerryPi reward modules remotely through a client

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

    new_licks = pyqtSignal(int)

    def __init__(self, client, module):
        super(RPIRewardControl, self).__init__()

        self.module = module
        self.client = client
    
        vlayout= QVBoxLayout()

        # module name
        module_label = QLabel(self.module)
        vlayout.addWidget(module_label)

        # pump name
        pump_name = self.client.get(f"modules['{self.module}'].pump.name")
        pump_label = QLabel(f"Pump: {pump_name}")
        vlayout.addWidget(pump_label)

        # widget to display and reset lick count
        lick_layout = QHBoxLayout()
        self.lick_count_n = int(self.client.get(f"modules['{self.module}'].lickometer.licks"))
        self.lick_count = QLabel(f"Lick Count: {self.lick_count_n}")
        lick_layout.addWidget(self.lick_count)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_licks)
        lick_layout.addWidget(reset_btn)
        vlayout.addLayout(lick_layout)
        self.lick_thread = RPIRewardControl.RPILickThread(self.client, self.module)
        self.lick_thread.lick_num_updated.connect(self._update_licks)
        self.lick_thread.start()

        # widget to control post reward delay
        post_delay_layout = QHBoxLayout()
        post_delay_layout.addWidget(QLabel("Post Reward Delay (s): "))
        self.post_delay = QLineEdit()
        self.post_delay.setValidator(QDoubleValidator())
        self.post_delay.setText(str(self.client.get(f"modules['{self.module}'].post_delay")))
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
        self.small_pulse_frac.setValidator(only_frac) # this doesn't seem to be working for some reason
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
        init_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
        self.led_btn.setChecked(init_state)
        self.led_btn.clicked.connect(self.toggle_led)
        vlayout.addWidget(self.led_btn)

        # button to toggle the valve
        self.valve_btn = QPushButton("Toggle Valve")
        self.valve_btn.setCheckable(True)
        init_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
        self.valve_btn.setChecked(init_state)
        self.valve_btn.clicked.connect(self.toggle_valve)
        vlayout.addWidget(self.valve_btn)

        # some formatting
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(2)
        self.setLayout(vlayout)
    
    def _update_licks(self, amt):
        if amt > 0: self.new_licks.emit(amt)
        self.lick_count_n += amt
        self.lick_count.setText(f"Lick Count: {self.lick_count_n}")

    def _single_pulse(self):
        self.trigger_reward(float(self.amt.text()))

    def _small_pulse(self):
        self.trigger_reward(float(self.small_pulse_frac.text()) * float(self.amt.text()))

    def reset_licks(self) -> None:
        """
        reset the lick count for this module
        """

        self.client.run_command("reset_licks", {'module': self.module}, channel = "run")
    
    def update_post_delay(self, post_delay:float = None) -> None:
        """
        update the time to wait post pump actuation before closing the
        valve associated to a module

        Args:
            post_delay: float (optional)
                new post pump actuation delay in seconds
        """

        post_delay = post_delay if post_delay is not None else float(self.post_delay.text())
        args = {'module': self.module,
                'post_delay': post_delay}
        self.client.run_command('update_post_delay', args, channel = 'run')
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

        args = {'module': self.module,
                'freq': freq,
                'dur': dur,
                'volume': volume}
        
        status = self.client.run_command('play_tone', args, channel = 'run')

        if not status=='SUCCESS\n':
            print('error status', status)

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
            led_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
            on = not led_state
        
        args = {'module': self.module,
                'on': on}
        status = self.client.run_command('toggle_LED', args, channel = 'run')
        if not status=='SUCCESS\n': print('error status', status)
        led_state = bool(self.client.get(f"modules['{self.module}'].LED.on"))
        self.led_btn.setChecked(led_state)

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
            valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
            open_valve = not valve_state
        args = {'module': self.module,
                'open_valve': open_valve}
        status = self.client.run_command('toggle_valve', args, channel = 'run')
        if not status=='SUCCESS\n': print('error status', status)
        valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open"))
        self.valve_btn.setChecked(valve_state)
        
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

        args = {'module': self.module, 
                'amount': amount,
                'force': force,
                'enqueue' : enqueue}
        status = self.client.run_command("trigger_reward", args, channel = 'run')
        if not status=='SUCCESS\n':
            print('error status', status)

    class RPILickThread(QThread):
        """
        thread to monitor licks on the pi

        ...
        PyQt Signals

        lick_num_updated(int)

        """

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