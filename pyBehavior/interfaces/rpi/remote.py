from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QGroupBox, QSizePolicy, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QComboBox, QTabWidget
from PyQt5.QtGui import QDoubleValidator
import time
from pyBehavior.gui import RewardWidget
import typing


class PumpConfig(QGroupBox):
    """

    a widget for controlling a pump on the ratBerryPi remotely
    through a client

    """
    def __init__(self, client, pump, parent, modules = None):
        super(PumpConfig, self).__init__()
        self.client = client
        self.pump = pump
        self.modules = modules
        self.parent = parent

        vlayout = QVBoxLayout()

        # pump name
        self.setTitle(self.pump)

        # label to keep track of the pump piston position
        playout = QHBoxLayout()
        playout.addWidget(QLabel("Position [cm]: "))
        self.pos_label = QLineEdit()
        self.pos_label.setEnabled(False)
        playout.addWidget(self.pos_label)
        vlayout.addLayout(playout)
        self.pos_thread = PumpConfig.RPIPumpPosThread(self.client, self.pump)
        self.pos_thread.pos_updated.connect(self._update_pos)
        self.pos_thread.start()

        # button to calibrate the pump
        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.calibrate)
        vlayout.addWidget(self.calibrate_btn)

        tabs = QTabWidget()
        settings_tab = QWidget()
        slayout = QVBoxLayout()

        # widget to select syringe
        syringe_layout = QHBoxLayout()
        syringe_label = QLabel("Syringe Type:")
        self.syringe_select = QComboBox()
        self.syringe_select.addItems(["BD1mL", "BD3mL", "BD5mL", "BD10mL", "BD30mL"])
        cur_syringe = self.client.get(f"pumps['{self.pump}'].syringe.syringeType", channel = 'run')
        self.syringe_select.setCurrentIndex(self.syringe_select.findText(cur_syringe))
        self.syringe_select.currentIndexChanged.connect(lambda x: self.change_syringe(None))
        syringe_layout.addWidget(syringe_label)
        syringe_layout.addWidget(self.syringe_select)
        slayout.addLayout(syringe_layout)

        # widget to change step type
        step_type_layout = QHBoxLayout()
        step_type_label = QLabel("Microstep Type: ")
        self.step_type_select = QComboBox()
        self.step_type_select.addItems(['Full', 'Half', '1/4', '1/8', '1/16', '1/32'])
        cur_microstep = self.client.get(f"pumps['{self.pump}'].stepType", channel = 'run')
        self.step_type_select.setCurrentIndex(self.step_type_select.findText(cur_microstep))
        self.step_type_select.currentIndexChanged.connect(lambda x: self.set_microstep_type(None))
        step_type_layout.addWidget(step_type_label)
        step_type_layout.addWidget(self.step_type_select)
        slayout.addLayout(step_type_layout)

        #widget to set step speed
        step_speed_layout = QHBoxLayout()
        step_speed_label = QLabel("Microstep Rate (steps/s): ")
        self.step_speed = QLineEdit()
        self.step_speed.setValidator(QDoubleValidator())
        cur_speed =self.client.get(f"pumps['{self.pump}'].speed", channel = 'run')
        self.step_speed.setText(f"{cur_speed}")
        self.step_speed.editingFinished.connect(self.set_step_speed)
        step_speed_layout.addWidget(step_speed_label)
        step_speed_layout.addWidget(self.step_speed)
        slayout.addLayout(step_speed_layout)

        #widget to set flow rate
        flow_rate_layout = QHBoxLayout()
        flow_rate_label = QLabel("Flow Rate (mL/s): ")
        self.flow_rate = QLineEdit()
        self.flow_rate.setValidator(QDoubleValidator())
        cur_flow_rate =self.client.get(f"pumps['{self.pump}'].flow_rate", channel = 'run')
        self.flow_rate.setText(f"{cur_flow_rate}")
        self.flow_rate.editingFinished.connect(self.set_flow_rate)
        flow_rate_layout.addWidget(flow_rate_label)
        flow_rate_layout.addWidget(self.flow_rate)
        slayout.addLayout(flow_rate_layout)

        # widget to control auto-fill
        auto_fill_layout = QHBoxLayout()
        auto_fill_thresh_label = QLabel("Auto Fill Threshold Fraction: ")
        self.auto_fill_thresh = QLineEdit()
        self.auto_fill_thresh.setText(f"{self.client.get('auto_fill_frac_thresh', channel = 'run')}")
        self.auto_fill_thresh.setValidator(QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation))
        self.auto_fill_thresh.editingFinished.connect(self.set_auto_fill_frac_thresh)
        self.auto_fill_btn = QPushButton("Toggle Auto-Fill")
        self.auto_fill_btn.setCheckable(True)
        init_state = bool(self.client.get(f"auto_fill", channel = 'run'))
        self.auto_fill_btn.setChecked(init_state)
        self.auto_fill_btn.clicked.connect(self.toggle_auto_fill)
        auto_fill_layout.addWidget(auto_fill_thresh_label)
        auto_fill_layout.addWidget(self.auto_fill_thresh)
        slayout.addLayout(auto_fill_layout)
        slayout.addWidget(self.auto_fill_btn)

        settings_tab.setLayout(slayout)
        tabs.addTab(settings_tab, "Settings")

        ctl_tab = QWidget()
        clayout = QVBoxLayout()

        # button to fill the lines
        self.fill_btn = QPushButton("Fill Lines")
        self.fill_btn.clicked.connect(lambda x: self.fill_lines())
        clayout.addWidget(self.fill_btn)

        # button to fill all the lines
        self.fill_all_btn = QPushButton("Fill all lines")
        self.fill_all_btn.clicked.connect(lambda x: self.fill_lines(fill_all = True))
        clayout.addWidget(self.fill_all_btn)

        # widget to push some fluid to the reservoir
        push_box = QGroupBox()
        push_layout = QVBoxLayout()
        push_box.setTitle("Push To Reservoir")
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
        push_layout.addLayout(push_res_layout)
        push_box.setLayout(push_layout)
        clayout.addWidget(push_box)

        # button to empty all of the lines
        self.empty_btn = QPushButton("Empty Lines")
        self.empty_btn.clicked.connect(self.empty_lines)
        clayout.addWidget(self.empty_btn)
        ctl_tab.setLayout(clayout)
        tabs.addTab(ctl_tab, "Control")

        # some formatting
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)

    def _update_pos(self, pos:float) -> None:
        self.pos_label.setText(f"{pos:.3f}")

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

        on = on if on is not None else not bool(self.client.get(f"auto_fill", channel = 'run'))
        self.client.run_command('toggle_auto_fill', {'on': on}, channel = 'run')
        time.sleep(.1)
        self.auto_fill_btn.setChecked(bool(self.client.get(f"auto_fill", channel = 'run')))

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

    def set_microstep_type(self, step_type:str = None) -> None:
        """
        set microstepping level of the pump
        
        Args:
            step_type: str
                type of microstepping to set the motor to. 
                must be a value listed in ratBerryPi.resources.pump.Pump.step_types:
                ['Full', 'Half', '1/4', '1/8', '1/16', '1/32']

        """
        step_type = step_type if step_type is not None else self.step_type_select.currentText()
        idx = self.step_type_select.findText(step_type)
        if idx == -1:
            raise ValueError('Invalid syringe type specified')
        
        args = {
            'pump': self.pump,
            'stepType': step_type
        }
        self.client.run_command('set_microstep_type', args, channel = 'run')
        self.step_type_select.setCurrentIndex(idx)
        flow_rate = float(self.client.get(f"pumps['{self.pump}'].flow_rate", channel = self.pump))
        self.flow_rate.setText(f"{flow_rate}")

    def set_step_speed(self, speed:float=None) -> None:
        """
        set the flow rate of the pump
        """
        speed = speed if speed is not None else float(self.step_speed.text())     
        args = {
            'pump': self.pump,
            'speed': speed
        }
        self.client.run_command('set_step_speed', args, channel = 'run')
        self.step_speed.setText(f"{speed}")
        flow_rate = float(self.client.get(f"pumps['{self.pump}'].flow_rate", channel = self.pump))
        self.flow_rate.setText(f"{flow_rate}")


    def set_flow_rate(self, flow_rate:float=None) -> None:
        """
        set the flow rate of the pump
        """
        flow_rate = flow_rate if flow_rate is not None else float(self.flow_rate.text())     
        args = {
            'pump': self.pump,
            'flow_rate': flow_rate
        }
        self.client.run_command('set_flow_rate', args, channel = 'run')
        flow_rate = float(self.client.get(f"pumps['{self.pump}'].flow_rate", channel = self.pump))
        self.flow_rate.setText(f"{flow_rate}")
        speed = float(self.client.get(f"pumps['{self.pump}'].speed", channel = self.pump))
        self.step_speed.setText(f"{speed}")

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
        flow_rate = float(self.client.get(f"pumps['{self.pump}'].flow_rate", channel = self.pump))
        self.flow_rate.setText(f"{flow_rate}")

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
    A widget for controlling ratBerryPi reward modules remotely through a client.
    """

    new_licks = pyqtSignal(int)

    def __init__(self, client, module, parent):
        super(RPIRewardControl, self).__init__()

        self.module = module
        self.client = client
        self.parent = parent

        self.setTitle(self.module)
        vlayout = QVBoxLayout()
        vlayout.setSpacing(8)

        # ── Pump readout ───────────────────────────────────────────────
        pump_row = QHBoxLayout()
        pump_lbl = QLabel("Pump")
        pump_lbl.setFixedWidth(40)
        pump_name = self.client.get(f"modules['{self.module}'].pump.name", channel='run')
        pump_le = QLineEdit(pump_name)
        pump_le.setEnabled(False)
        pump_row.addWidget(pump_lbl)
        pump_row.addWidget(pump_le)
        vlayout.addLayout(pump_row)

        # ── Lick counter ───────────────────────────────────────────────
        lick_group = QGroupBox()
        lick_group.setTitle("Lick Counter")
        lick_vlayout = QVBoxLayout()
        lick_vlayout.setSpacing(4)
        self.lick_count_n = int(self.client.get(f"modules['{self.module}'].lickometer.licks", channel='run'))
        self.lick_count = QLineEdit(f"{self.lick_count_n}")
        self.lick_count.setEnabled(False)
        self.lick_count.setAlignment(Qt.AlignCenter)
        self.lick_count.setStyleSheet("font-size: 20px; font-weight: bold; min-height: 36px;")
        lick_vlayout.addWidget(self.lick_count)
        reset_lick_btn = QPushButton("Reset Lick Count")
        reset_lick_btn.clicked.connect(self.reset_licks)
        lick_vlayout.addWidget(reset_lick_btn)
        lick_group.setLayout(lick_vlayout)
        vlayout.addWidget(lick_group)

        self.lick_thread = RPIRewardControl.RPILickThread(self.client, self.module)
        self.lick_thread.lick_num_updated.connect(self._update_licks)
        self.lick_thread.start()

        # ── Session stats ──────────────────────────────────────────────
        stats_group = QGroupBox()
        stats_group.setTitle("Session Stats")
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)
        for label_text, attr in [("Volume (mL)", "amt_disp"), ("# Pulses", "npulse")]:
            col = QVBoxLayout()
            col_label = QLabel(label_text)
            col_label.setAlignment(Qt.AlignCenter)
            le = QLineEdit("0")
            le.setEnabled(False)
            le.setAlignment(Qt.AlignCenter)
            le.setStyleSheet("font-size: 15px; font-weight: bold;")
            setattr(self, attr, le)
            col.addWidget(col_label)
            col.addWidget(le)
            stats_layout.addLayout(col)
        stats_reset_btn = QPushButton("Reset")
        stats_reset_btn.setFixedWidth(52)
        stats_reset_btn.clicked.connect(lambda x: self.reset_amount_dispensed())
        stats_layout.addWidget(stats_reset_btn)
        stats_group.setLayout(stats_layout)
        vlayout.addWidget(stats_group)

        # ── Controls group ─────────────────────────────────────────────
        ctrl_group = QGroupBox()
        ctrl_group.setTitle("Controls")
        hlayout = QHBoxLayout()
        hlayout.setSpacing(8)

        tabs = QTabWidget()

        # Reward tab
        reward_tab = QWidget()
        rlayout = QVBoxLayout()
        rlayout.setSpacing(6)
        post_row = QHBoxLayout()
        post_row.addWidget(QLabel("Post-reward delay (s)"))
        self.post_delay = QLineEdit()
        self.post_delay.setValidator(QDoubleValidator())
        self.post_delay.setText(str(self.client.get(f"modules['{self.module}'].post_delay", channel='run')))
        self.post_delay.setFixedWidth(60)
        self.post_delay.editingFinished.connect(self.update_post_delay)
        post_row.addStretch()
        post_row.addWidget(self.post_delay)
        rlayout.addLayout(post_row)
        pulse_row = QHBoxLayout()
        pulse_row.addWidget(QLabel("Pulse amount (mL)"))
        self.amt = QLineEdit("0.2")
        self.amt.setValidator(QDoubleValidator())
        self.amt.setFixedWidth(60)
        pulse_row.addStretch()
        pulse_row.addWidget(self.amt)
        rlayout.addLayout(pulse_row)
        only_frac = QDoubleValidator(0., 1., 6, notation=QDoubleValidator.StandardNotation)
        small_row = QHBoxLayout()
        small_row.addWidget(QLabel("Small pulse fraction"))
        self.small_pulse_frac = QLineEdit("0.6")
        self.small_pulse_frac.setValidator(only_frac)
        self.small_pulse_frac.setFixedWidth(60)
        small_row.addStretch()
        small_row.addWidget(self.small_pulse_frac)
        rlayout.addLayout(small_row)
        rlayout.addStretch()
        reward_tab.setLayout(rlayout)
        tabs.addTab(reward_tab, "Reward")

        # Tone tab
        tone_tab = QWidget()
        tlayout = QVBoxLayout()
        tlayout.setSpacing(6)
        for label_text, attr, default in [
            ("Frequency (Hz)", "tone_freq", "800"),
            ("Duration (s)", "tone_dur", "1"),
            ("Volume (0–1)", "tone_vol", "1"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            le = QLineEdit(default)
            le.setValidator(QDoubleValidator())
            le.setFixedWidth(60)
            setattr(self, attr, le)
            row.addStretch()
            row.addWidget(le)
            tlayout.addLayout(row)
        tlayout.addStretch()
        tone_tab.setLayout(tlayout)
        tabs.addTab(tone_tab, "Tone")
        hlayout.addWidget(tabs, stretch=2)

        # Action buttons column
        clayout = QVBoxLayout()
        clayout.setSpacing(5)
        pulse_btn = QPushButton("Pulse")
        pulse_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pulse_btn.clicked.connect(self._single_pulse)
        small_pulse_btn = QPushButton("Small\nPulse")
        small_pulse_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        small_pulse_btn.clicked.connect(self._small_pulse)
        tone_btn = QPushButton("Play\nTone")
        tone_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tone_btn.clicked.connect(lambda x: self.play_tone())
        self.led_btn = QPushButton("LED")
        self.led_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.led_btn.setCheckable(True)
        init_led = bool(self.client.get(f"modules['{self.module}'].LED.on", channel='run'))
        self.led_btn.setChecked(init_led)
        self.led_btn.clicked.connect(self.toggle_led)
        self.valve_btn = QPushButton("Valve")
        self.valve_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.valve_btn.setCheckable(True)
        init_valve = bool(self.client.get(f"modules['{self.module}'].valve.is_open", channel='run'))
        self.valve_btn.setChecked(init_valve)
        self.valve_btn.clicked.connect(self.toggle_valve)
        for btn in (pulse_btn, small_pulse_btn, tone_btn, self.led_btn, self.valve_btn):
            clayout.addWidget(btn)
        hlayout.addLayout(clayout, stretch=1)
        ctrl_group.setLayout(hlayout)
        vlayout.addWidget(ctrl_group)
        self.setLayout(vlayout)

    def reset_amount_dispensed(self):
        self.amt_disp.setText(f"{0}")
        self.npulse.setText(f"{0}")
    
    def _update_licks(self, amt):
        if amt > 0: self.new_licks.emit(amt)
        self.lick_count_n += amt
        self.lick_count.setText(f"{self.lick_count_n}")

    def _single_pulse(self):
        amt = float(self.amt.text())
        self.parent.log(f"manually pulsing {amt} mL to {self.module}")
        self.trigger_reward(amt)

    def _small_pulse(self):
        amt = float(self.small_pulse_frac.text()) * float(self.amt.text())
        self.parent.log(f"manually pulsing {amt} mL to {self.module}")
        self.trigger_reward(amt)

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
            led_state = bool(self.client.get(f"modules['{self.module}'].LED.on", channel = 'run'))
            on = not led_state
        
        args = {'module': self.module,
                'on': on}
        status = self.client.run_command('toggle_LED', args, channel = 'run')
        if not status=='SUCCESS\n': print('error status', status)
        led_state = bool(self.client.get(f"modules['{self.module}'].LED.on", channel = 'run'))
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
            valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open", channel = 'run'))
            open_valve = not valve_state
        args = {'module': self.module,
                'open_valve': open_valve}
        status = self.client.run_command('toggle_valve', args, channel = 'run')
        if not status=='SUCCESS\n': print('error status', status)
        valve_state = bool(self.client.get(f"modules['{self.module}'].valve.is_open", channel = 'run'))
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
        self.amt_disp.setText(f"{float(self.amt_disp.text()) + amount}")
        self.npulse.setText(f"{float(self.npulse.text()) + 1}")

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