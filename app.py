
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog, QListWidget, QDialogButtonBox, QScrollArea
from PyQt5.QtCore import Qt
import numpy as np
import pandas as pd
from utils import *
from pathlib import Path
import nidaqmx


class filenameDialog(QDialog):
    def __init__(self):
        super(filenameDialog, self).__init__()

        self.fname = None
        buttonBox = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.check_input)
        cancel.clicked.connect(self.reject)
        buttonBox.addWidget(ok)
        buttonBox.addWidget(cancel)

        layout = QVBoxLayout()
        self.fname_input = QLineEdit()
        message = QLabel("Please enter a name for the port mapping. Avoid all symbols except for - and _")
        layout.addWidget(message)
        layout.addWidget(self.fname_input)
        layout.addLayout(buttonBox)
        self.setLayout(layout)
    
    def check_input(self):
        self.fname = self.fname_input.text()
        valid = (len(self.fname)>1) & np.all([x.isalnum() or x in [" ", "-", "_"] for x in self.fname])
        if valid:
            self.accept()


class Settings(QMainWindow):
    def __init__(self):
        super(Settings, self).__init__()

        # create layout elements
        self.layout = QVBoxLayout()
        self.header_layout = QHBoxLayout()

        # get default map file
        self.params = np.load('params.npy', allow_pickle = True).item()
        self.map_file = self.params['prev_edited']
        self.mapping = pd.read_csv(self.map_file)
        self.mapping = self.mapping.set_index('port')['name'].fillna("")
        
        # create a drop down menu of available mappings
        self.map_file_select = QComboBox()
        available_mappings = [i.stem for i in Path('port-mappings').iterdir()]
        self.map_file_select.addItems(available_mappings)
        self.map_file_select.setCurrentIndex(available_mappings.index(Path(self.map_file).stem)) # set the default as the one in the params file
        self.map_file_select.currentIndexChanged.connect(self.change_map_file)
        self.header_layout.addWidget(self.map_file_select)

        # button to create new map file
        self.create_btn = QPushButton("create")
        self.create_btn.clicked.connect(self.create)
        self.header_layout.addWidget(self.create_btn)

        # button to save current mappings to selected map file
        self.save_btn = QPushButton("save")
        self.save_btn.clicked.connect(self.save)
        self.header_layout.addWidget(self.save_btn)
        self.layout.addLayout(self.header_layout)

        # fill the body of the window with port labels and inputs for names to assign
        self.body_layout = QHBoxLayout()
        self.name_input_layout = QVBoxLayout()
        self.port_label_layout = QVBoxLayout()
        self.del_btns_layout = QVBoxLayout()
        self.fill_body()
        self.body_layout.addLayout(self.port_label_layout)
        self.body_layout.addLayout(self.name_input_layout)
        self.body_layout.addLayout(self.del_btns_layout)
        self.body_widget = QWidget()       
        self.body_widget.setLayout(self.body_layout)
        # make it scrollable
        self.scroll = QScrollArea() 
        self.scroll.setWidget(self.body_widget)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)

        #add the widget
        self.layout.addWidget(self.scroll)


        #TODO: need a button to add ports
        # make sure its not possible to add an already listed port
        # also make sure the port exists?

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
    
    def fill_body(self):
        """
        fill the body of the window with label 
        and line edit widgets for all mappings
        """
        self.port_labels = []
        self.name_inputs = []
        self.del_btns = []
        for port, name in self.mapping.iteritems():

            port_label = QLabel()
            port_label.setText(port)
            self.port_labels.append(port_label)

            name_input = QLineEdit()
            name_input.setText(name)
            name_input.editingFinished.connect(self.update_var_name)
            self.name_inputs.append(name_input)


            del_btn = QPushButton("del")
            del_btn.clicked.connect(self.del_map)
            self.del_btns.append(del_btn)

            self.port_label_layout.addWidget(port_label) 
            self.name_input_layout.addWidget(name_input)
            self.del_btns_layout.addWidget(del_btn)
        
    def update_var_name(self):
        line = self.name_inputs.index(self.sender())
        self.mapping.iloc[line] = self.name_inputs[line].text()

    def save(self):
        self.mapping.to_frame().to_csv(self.map_file)
    
    def create(self):
        # new_mapping = pd.read_csv('port-mappings/blank.csv').set_index('port')['name'].fillna("")
        # use 
        try:
            system = nidaqmx.system.System.local()
            channels = []
            for dev in system.devices:
                # get some list of all channels on this device
                # channels.extend(...)
                continue
            new_mapping = pd.Series([""]* len(channels), index = channels)
        except nidaqmx._lib.DaqNotFoundError: # for debugging purposes if not running on the machine itself
            new_mapping = pd.read_csv('port-mappings/blank.csv').set_index('port')['name'].fillna("")
            new_mapping.loc[:] = ""

        dialog = filenameDialog()
        dialog.exec_()

        if dialog.fname is not None:
            new_map_file = f'port-mappings/{dialog.fname}.csv'
            new_mapping.to_frame().to_csv(new_map_file)
            self.map_file_select.addItems([dialog.fname])
            self.map_file_select.setCurrentText(dialog.fname)

    def change_map_file(self):

        for i in range(len(self.port_labels)):
            self.port_labels[i].deleteLater()
            self.name_inputs[i].deleteLater()
            self.del_btns[i].deleteLater()

        self.map_file = f'port-mappings/{str(self.map_file_select.currentText())}.csv'
        self.params['prev_edited'] = self.map_file
        np.save('params.npy', self.params)
        self.mapping = pd.read_csv(self.map_file).set_index('port')['name'].fillna("")
        self.fill_body()        

    def del_map(self):
        line = self.del_btns.index(self.sender())
        self.port_labels[line].deleteLater()
        self.name_inputs[line].deleteLater()
        self.del_btns[line].deleteLater()
        self.mapping.drop(index = self.mapping.index[line], inplace=True)



class SetupDialog(QDialog):
    def __init__(self):
        super(SetupDialog, self).__init__()
        setups = [x.name for x in Path('setups').iterdir() if x.is_dir()]

        layout = QVBoxLayout()
        self.setup_select = QListWidget()
        self.setup_select.addItems(setups)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout.addWidget(self.setup_select)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    



        


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        # create settings button
        self.setWindowTitle("My App")
        self.settings_btn = QPushButton("Edit Mappings")
        self.settings_dialog = Settings() # instantiate settings dialog window
        self.settings_btn.clicked.connect(self.open_settings_dialog)


        self.setup_btn = QPushButton("Select Setup")
        self.setup_btn.clicked.connect(self.open_setup_dialog)

        layout = QVBoxLayout()
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.setup_btn)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def open_settings_dialog(self):
        self.settings_dialog.show()

    def open_setup_dialog(self):
        dialog = SetupDialog()
        dialog.exec_()
        # should check if they clicked ok first
        setup = dialog.setup_select.currentItem().text()
        import importlib
        params = np.load(Path('setups')/setup/'params.npy', allow_pickle=True).item()
        setup_mod = importlib.import_module(f'setups.{setup}.visualizer')
        Visualizer = getattr(setup_mod, params['vis-name'])
        self.visualizer = Visualizer((Path('setups')/setup).as_posix())
        self.visualizer.show()
        # given the selected setup should open the appropriate visualizer


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()