from nidaqmx import constants, Task
import logging
import matplotlib.pyplot as plt
import time
from PyQt5.QtCore import QThread, pyqtSignal
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QDialog
from utils import *

logging.basicConfig(format = "%(asctime)s-%(levelname)s: %(message)s", level = logging.DEBUG)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(640, 480)
    window.show()
    sys.exit(app.exec_())
