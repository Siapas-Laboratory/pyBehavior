
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
import numpy as np
import pandas as pd
from utils import *
from pathlib import Path


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
        self.body_layout = QHBoxLayout()
        self.name_input_layout = QVBoxLayout()
        self.port_label_layout = QVBoxLayout()
        self.del_btns_layout = QVBoxLayout()


        # get default map file
        self.params = np.load('params.npy', allow_pickle = True).item()
        self.map_file = self.params['map-file']

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

        # load the currently selected map file
        # TODO: need to wrap this in a try except clause to make sure 'port' is an existing  column
        # just in case people want to edit the csv in excel
        self.mapping = pd.read_csv(self.map_file).set_index('port')['name'].fillna("")
        self.fill_body()
        
        self.body_layout.addLayout(self.port_label_layout)
        self.body_layout.addLayout(self.name_input_layout)
        self.body_layout.addLayout(self.del_btns_layout)
        self.layout.addLayout(self.body_layout)

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
        self.params['map-file'] = self.map_file
        np.save('params.npy', self.params)
        self.mapping = pd.read_csv(self.map_file).set_index('port')['name'].fillna("")
        self.fill_body()        

    def del_map(self):
        line = self.del_btns.index(self.sender())
        self.port_labels[line].deleteLater()
        self.name_inputs[line].deleteLater()
        self.del_btns[line].deleteLater()
        self.mapping.drop(index = self.mapping.index[line], inplace=True)



class Protocols(QMainWindow):
    def __init__(self):
        super(Protocols, self).__init__()

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        # create settings button
        self.setWindowTitle("My App")
        self.settings_btn = QPushButton("settings")
        self.settings_dialog = Settings() # instantiate settings dialog window
        self.settings_btn.clicked.connect(self.open_settings_dialog)


        self.protocols_btn = QPushButton("protocols")
        self.protocols_dialog = Protocols() # instantiate protocols dialog window
        self.protocols_btn.clicked.connect(self.open_protocols_dialog)

        layout = QVBoxLayout()
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.protocols_btn)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def open_settings_dialog(self):
        self.settings_dialog.show()

    def open_protocols_dialog(self):
        self.protocols_dialog.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()