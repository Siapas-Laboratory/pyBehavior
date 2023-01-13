import nidaqmx
from nidaqmx import constants
from nidaqmx import stream_readers
from nidaqmx import stream_writers
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
from utils import *

fs_acq = 1000

# # i should probably subclass QMainWindow to define a template for these protocol GUIS that can be 
# # subclassed for writing  protocols
# class MainWindow(QMainWindow):

#     def __init__(self):
#         super(MainWindow, self).__init__()
        
#         # need to create the GUI elements here

#         _, _, self.mapping = load_mapping()
#             # TODO: need to validate that a valid port-map file has been selected

#         self.mapping = self.mapping.set_index('name')['port'].fillna("")
#         beam_strs = [f'beam{i}' for i in range(1,13)]
#         beams = pd.DataFrame({'port': self.mapping.loc[beam_strs].values}, index = beam_strs)
#         # also need a column for the appropriate gui elements for each beam
#         beams['state'] = np.zeros(beams.shape[0])

#         # we need to acquire one sample at a time from all beam channels
#         # compare the state to the current state and if it is different update the gui element

# this should occur within a separate thread i think
# this is where any  code involving the 

_, _, mapping = load_mapping()
mapping = mapping.set_index('name')['port'].fillna("")
beam_strs = [f'beam{i}' for i in range(1,13)]
beam_ports = mapping.loc[beam_strs]
beam_states = np.zeros((len(beam_strs),))
with nidaqmx.Task() as task:
    for beam,port in beam_ports.items():
        task.ai_channels.add_ai_accel_chan(port,  name_to_assign_to_channel = beam)
    task.timing.cfg_samp_clk_timing(rate=fs_acq, sample_mode=constants.AcquisitionType.CONTINUOUS)

    reader = stream_readers.AnalogMultiChannelReader(task.in_stream)
    writer = stream_writers.AnalogMultiChannelWriter(task.out_stream)

    def update_states(task_idx, event_type, num_samples, callback_data=None):
        prev_beam_states = beam_states
        reader.read_single_sample(beam_states, num_samples, timeout=constants.WAIT_INFINITELY)
        changed_states = np.where(prev_beam_states!=beam_states)[1]
        print(changed_states)
        for i in changed_states:
            beam = f'beam{i+1}'
            #update the gui elements associated with this beam somehow

    # if this runs continuously, how do i stop it?
    task.register_every_n_samples_acquired_into_buffer_event(1, update_states)
