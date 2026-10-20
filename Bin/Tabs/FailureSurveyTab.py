from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtCharts import (
    QBarSeries, QChart, QChartView, QBarSet, QBarCategoryAxis, QValueAxis, QPieSeries
)
import re
import requests
from math import ceil

class FailureSurvey(QWidget):
    def getSeries(self) -> QPieSeries:
        n = len(self.FAILS[str(11072)])
        s = QPieSeries()
        for k, v in self.COUNT11072.items():
            if v / n > 0.01:
                s.append(k, v)
        
        s.setLabelsVisible(True)

        for s_ in s.slices():
            s_.setLabel(f"{s_.label()}: {(s_.value() / n * 100):.1f}%")

            s_.setLabelColor(QColor("#969696"))
            s_.setLabelBrush(QColor("#969696"))
        
        return s
    
    def count11072Types(self) -> None:
        pattern = re.compile(r"(.*)\[(?P<error>.*)\](.*)\[(?P<reason>.*)\](.*)\[(?P<type>.*)\]")
        for item in self.FAILS[str(11072)]:
            match = pattern.match(item['comment'])
            if match:
                gd = match.groupdict()
                reason = gd['reason']
                
                sub11072Type = reason.split('=')[0].strip()
                # COUNTER
                if sub11072Type in self.COUNT11072.keys():
                    self.COUNT11072[sub11072Type] += 1
                else:
                    self.COUNT11072[sub11072Type] = 1
    

    def __init__(self, url=r"http://127.0.0.1:8000"):
        super().__init__()
        self.GRID = QGridLayout(self)
        self.URL = url
        self.FAILS: dict[int, list[dict]] = requests.get(f"{self.URL}/failuresurvey").json()
        self.TOTAL = self.FAILS['total']
        del self.FAILS['total']

        # HEADER
        self.HEADER = QLabel("Error Description")
        self.HEADER.setObjectName('subheader')

        # TABLE
        self.TABLE = QTableWidget()
        self.TABLE.setRowCount(6)
        self.TABLE.setColumnCount(3)
        self.TABLE.setHorizontalHeaderLabels(["Error Code", "Reason", "Avoidable"])
        rows = [("1085", r"Unable to copy file to E:\Temp", "Yes"),
                ("10011", "Volume Full Error", "Yes"),
                ("96063", "Duplicated ID Error", "No (Non-Critical)"),
                ("11072", "Missing attribute in database", "Pending Investigation"),
                ("41178", "FSC Proxy Error", "Pending Investigation"),
                ("100254", "FSC error writing object_metadata.xml in Giman_Trans", "No"),
                ("515009", "A POM Internal Error has occured", "No") ]

        for i, row in enumerate(rows):
            for j, lab in enumerate(row):
                item = QTableWidgetItem(lab)
                self.TABLE.setItem(i, j, item)

        self.TABLE.resizeColumnsToContents()
        
        # BAR GRAPH
        self.BAR_SERIES = QBarSeries()
        maximum = 0 
        for k, v in self.FAILS.items():
            n = len(v)
            maximum = n if n > maximum else maximum
            if n / self.TOTAL > .01:
                qSet = QBarSet(str(k))
                qSet.append([n])
                self.BAR_SERIES.append(qSet)

        self.BARS = QChart()
        self.BARS.addSeries(self.BAR_SERIES)
        self.BARS.setTitle("Errors By Category")
        self.BARS.legend().setVisible(True)
        
        self.BARS.legend().setAlignment(Qt.AlignmentFlag.AlignTop)

        self.BARS.setBackgroundBrush(QColor("#000000"))
        self.BARS.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self.YAXIS = QValueAxis()
        
        self.YAXIS.setRange(0, ceil(maximum / 1000) * 1000)
        self.YAXIS.setTickCount(int(ceil(maximum / 1000) / 4))
        self.YAXIS.setGridLineVisible(True)
        self.BARS.addAxis(self.YAXIS, Qt.AlignmentFlag.AlignLeft)
        self.BAR_SERIES.attachAxis(self.YAXIS)

        self.BARS_VIEW = QChartView(self.BARS)
        
        


        # PIE CHART
        self.PIE = QChart()
        self.COUNT11072 = dict()
        self.count11072Types()
        self.PIE_SERIES = self.getSeries()
        self.PIE.addSeries(self.PIE_SERIES)
        self.PIE.setTitle("Sub-Types of 11702 Errors")
        self.PIE.setTitleBrush(QColor("#969696"))
        self.PIE.setBackgroundBrush(QColor("#000000"))
        self.PIE.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self.PIE.legend().setVisible(True)
        self.PIE_VIEW = QChartView(self.PIE)
        
        self.GRID.addWidget(self.HEADER, 0, 0, 1, 2)
        self.GRID.addWidget(self.TABLE, 1, 0, 1, 2)
        self.GRID.addWidget(self.BARS_VIEW, 2, 0)
        self.GRID.addWidget(self.PIE_VIEW, 2, 1)
        self.GRID.setRowStretch(0, 1)
        self.GRID.setRowStretch(1, 2)
        self.GRID.setRowStretch(2, 5)
        