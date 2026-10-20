from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QCheckBox, QComboBox, QVBoxLayout, QLineEdit
)
from PyQt6.QtCharts import (
    QChart, QPieSeries, QChartView     
)

import pyqtgraph as pg
import numpy as np

class VolumeReviewTab(QWidget):
    def __init__(self):
        super().__init__()

        # GRID LAYOUT
        self.grid = QGridLayout(self)