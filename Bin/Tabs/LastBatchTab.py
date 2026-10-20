from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QRadioButton, QComboBox, QVBoxLayout, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtCharts import (
    QChart, QPieSeries, QChartView  
)
import re
import pyqtgraph as pg
import numpy as np
from BatchResult.ItemDetails import ItemDetails
from datetime import datetime
import requests

class LastBatch(QWidget):
    # dict[str, ItemDetails] = dict()
    def classifyNBatches(self) -> None:
        """
        Classify N Batches calls the API to query the last N batches, and modify a dictionary in the following form:
        self.BATCHES["%B %d, %Y at %H:%M:%S] = [ItemDetails]
        
        :param self: Description
        """
        data: dict[str, dict]= requests.get(f"{self.URL}/lastbatches/{self.N}").json()
        pattern = re.compile(r"(?P<site>.*)_(?P<Y>\d+)-(?P<m>\d+)-(?P<d>\d+)=(?P<H>\d+)-(?P<M>\d+)-(?P<S>\d+)_(?P<size>\d+)__(?P<order>\w+)")     

        for batch_id, map in data.items():
            match = pattern.match(batch_id)

            if match:
                gd = match.groupdict()
                date = [int(i) for i in [gd['Y'],gd['m'],gd['d'], gd['H'], gd['M'], gd['S']]]
                order = gd["order"]
                instant = datetime(*date)
                key = instant.strftime("%B %d, %Y at %H:%M:%S") + " - " + order 
            else:
                key = batch_id
            
            self.BATCHES[key] = {"oaat": map["oaat"], "duration": map["duration"]}

            
            # Performs duration calculations for one at a time processing
            if map["oaat"]:     
                timeFromStart = 0.0
                batch_list = []
                for item in map["items"]:
                    toAdd = ItemDetails(**item)
                    try:
                        timeFromStart += toAdd.DURATION
                    except TypeError:
                        pass
                    toAdd.setTFS(timeFromStart)
                    batch_list.append(toAdd)
                self.BATCHES[key]["items"] =  batch_list

            else:
                self.BATCHES[key]["items"] = [ItemDetails(**item) for item in map["items"]]
            

    def refreshClicked(self):
        self.classifyNBatches()
        self.COMBO_Batch.addItems([i for i in list(self.BATCHES.keys())[::-1]])


    def getDurationData(self) -> tuple[list, list]:
        batch: dict = self.BATCHES[self.COMBO_Batch.currentText()]
        oaat: bool = batch["oaat"]
        duration: int = batch["duration"]
        items: list[ItemDetails] = batch["items"]

        match oaat:
            case True:
                if self.RAD_Time.isChecked():
                    data = np.array([[i.TIME_FROM_START, i.DURATION] for i in items if i.DURATION is not None])
                    x = data[:, 0]
                    y = data[:, 1]

                elif self.RAD_Batch.isChecked():
                    data = np.array([[i, itemdetail.DURATION] for i, itemdetail in enumerate(items) if itemdetail.DURATION is not None])
                    x = data[:, 0]
                    y = data[:, 1]

            case False:
                n = len(items)
                avgDuration = duration / n      # INVESTIGATE 
                if self.RAD_Time.isChecked():
                    x = [0, duration]
                    y = [avgDuration, avgDuration]

                elif self.RAD_Batch.isChecked():
                    x = [0, n]
                    y = [avgDuration, avgDuration]
        
        return x, y

    
    def getSizeData(self):
        batch: dict = self.BATCHES[self.COMBO_Batch.currentText()]
        oaat: bool = batch["oaat"]
        duration: int = batch["duration"]
        items: list[ItemDetails] = batch["items"]
        
        match oaat:
            case True:
                if self.RAD_Time.isChecked():
                    data = np.array([[i.TIME_FROM_START, i.SIZE / 10e6] for i in items if i.SIZE is not None])
                    x = data[:, 0]
                    y = data[:, 1]

                elif self.RAD_Batch.isChecked():
                    data = np.array([[i, itemdetail.SIZE / 10e6] for i, itemdetail in enumerate(items) if itemdetail.SIZE is not None])
                    x = data[:, 0]
                    y = data[:, 1]

            case False:
                n = len(items)
                avgSize = sum([i.SIZE / 10e6 for i in items if i.SIZE is not None]) / n
                if self.RAD_Time.isChecked():
                    x = [0, duration]
                    y = [avgSize, avgSize]

                elif self.RAD_Batch.isChecked():
                    x = [0, n]
                    y = [avgSize, avgSize]
        
        return x, y
    

    def getSeries(self) -> QPieSeries:
        batch: list[ItemDetails] = self.BATCHES[self.COMBO_Batch.currentText()]["items"]
        s = QPieSeries()
        nSuccessful = len([i for i in batch if "SUCCESS" in i.STATUS])
        n = len(batch)
        nFail = n - nSuccessful
        s.append("Successful", nSuccessful) 
        if nSuccessful < n:
            s.append("Failed", nFail)
        s.setLabelsVisible(True)
        colorLabels = [("Succesuful", '#ffcdba'),("Failed",'#ff4600')]
        
        explodeFirst = True
        for s_, colorLabel in zip(s.slices(), colorLabels):
            if explodeFirst:
                s_.setExploded(True)
                s_.setExplodeDistanceFactor(.2)
            s_.setLabel(f"{colorLabel[0]} {(s_.value() / n * 100):.1f}%")
            s_.setBrush(QColor(colorLabel[1]))
            s_.setLabelColor(QColor("#969696"))
            s_.setLabelBrush(QColor("#969696"))
        
        return s


    def getHistogramDurationData(self, bins: int):
        batch: dict = self.BATCHES[self.COMBO_Batch.currentText()]
        oaat: bool = batch["oaat"]
        duration: int = batch["duration"]
        items: list[ItemDetails] = batch["items"]

        
        x = [i.DURATION for i in items if i.DURATION is not None and i.DURATION != 0] if oaat else [duration / len(items)]

        counts, bins = np.histogram(x, bins)

        return counts, bins
    
    def getHistogramSizeData(self, bins: int):
        batch: list[ItemDetails] = self.BATCHES[self.COMBO_Batch.currentText()]["items"]
        x = [i.SIZE / 10e6 for i in batch if i.SIZE is not None]
        counts, bins = np.histogram(x, bins)

        return counts, bins
    

    def refreshTimePerItem(self):
        """
        Updates 
        """
        x, y = self.getDurationData()
        self.LG_TimePerItem.removeItem(self.CURVE_TimePerItem)
        self.CURVE_TimePerItem = self.LG_TimePerItem.plot(x, y)

        if self.RAD_Time.isChecked():
            self.LG_TimePerItem.setLabel('bottom', 'Time Since Start', units='s')

        elif self.RAD_Batch.isChecked():
            self.LG_TimePerItem.setLabel('bottom', 'Batch Index')

        # Limit zoom/pan range
        xlim = max(x)
        ylim = max(y) * 1.2 

        self.VB_TimePerItem.setLimits(
            xMin=0,
            xMax=xlim,
            yMin=0,
            yMax=ylim
        )

    def refreshSizePerItem(self) -> None:

        x, y = self.getSizeData()
        self.LG_SizePerItem.removeItem(self.CURVE_SizePerItem)
        self.CURVE_SizePerItem = self.LG_SizePerItem.plot(x, y)

        if self.RAD_Time.isChecked():
            self.LG_SizePerItem.setLabel('bottom', 'Time Since Start', units='s')

        elif self.RAD_Batch.isChecked():
            self.LG_SizePerItem.setLabel('bottom', 'Batch Index')

        xlim = max(x)
        ylim = max(y) * 1.2

        self.VB_SizePerItem.setLimits(
            xMin=0,
            xMax=xlim,
            yMin=0,
            yMax=ylim
        )


    def refreshDurationHistogram(self):
        counts, bins = self.getHistogramDurationData(self.BINS)
        self.HIST_Duration.removeItem(self.HIST_LineDuration)
        self.HIST_LineDuration = pg.BarGraphItem(
            x=bins[:-1],
            height=counts,
            width=np.diff(bins),
        )
        self.HIST_Duration.addItem(self.HIST_LineDuration)


    def refreshSizeHistogram(self):
        counts, bins = self.getHistogramSizeData(self.BINS)
        self.HIST_Size.removeItem(self.HIST_LineSize)
        self.HIST_LineSize = pg.BarGraphItem(
            x=bins[:-1],
            height=counts,
            width=np.diff(bins),
        )
        self.HIST_Size.addItem(self.HIST_LineSize)

    def refreshPieChart(self):
        self.PIE_Statuses.removeAllSeries()
        s = self.getSeries()
        self.PIE_Statuses.addSeries(s)

    def radioClicked(self):
        self.refreshTimePerItem()
        self.refreshSizePerItem()
        self.refreshDurationHistogram()
        self.refreshSizeHistogram()
        self.refreshPieChart()

    def comboChanged(self):
        self.refreshTimePerItem()
        self.refreshSizePerItem()
        self.refreshDurationHistogram()
        self.refreshSizeHistogram()
        self.refreshPieChart()

    def __init__(self, n:int, url:str = r"http://127.0.0.1:8000"):
        super().__init__()
        # GRID LAYOUT
        self.BATCHES: dict[str, ItemDetails] = dict()
        self.N: int = n
        self.URL = url
        self.classifyNBatches()       
        self.GRID = QGridLayout(self)
        self.BINS = 100

    # CONTENTS
    # HEADER
        self.WGT_Header = QWidget()
        self.GRID_Header = QGridLayout(self.WGT_Header)
    

        self.LAB_HEADER = QLabel("Per Batch View")
        self.LAB_HEADER.setObjectName("header")
        self.LAB_SUBHEADER = QLabel(f"A means of viewing the last {n} batches performance")
        self.LAB_SUBHEADER.setObjectName("subheader")

        # START/STOP BUTTON
        self.BUT_Refresh = QPushButton("Refresh")
        self.BUT_Refresh.clicked.connect(self.refreshClicked)

        # ITEM COUNT COMBO BOX
        self.COMBO_Batch = QComboBox()
        self.COMBO_Batch.addItems([i for i in list(self.BATCHES.keys())])
        self.COMBO_Batch.setCurrentIndex(0)
        self.COMBO_Batch.currentTextChanged.connect(self.comboChanged)
        self.RAD_Time = QRadioButton("Per Time Domain")
        self.RAD_Time.setChecked(True)
        self.RAD_Time.clicked.connect(self.radioClicked)
        self.RAD_Batch = QRadioButton("Per Batch Domain")
        self.RAD_Batch.clicked.connect(self.radioClicked)

        self.GRID_Header.addWidget(self.LAB_HEADER, 0,0)
        self.GRID_Header.addWidget(self.LAB_SUBHEADER, 1,0)
        self.GRID_Header.addWidget(self.RAD_Time, 0,1)
        self.GRID_Header.addWidget(self.RAD_Batch, 1,1)
        self.GRID_Header.addWidget(self.COMBO_Batch, 0, 2)
        self.GRID_Header.addWidget(self.BUT_Refresh, 1, 2)
        self.GRID_Header.setColumnStretch(0, 2)
        self.GRID_Header.setColumnStretch(1, 1)
        self.GRID_Header.setColumnStretch(2, 1)

        

    # LEFT PANE
        self.WGT_LeftPane = QWidget()
        self.VSTACK_LeftPane = QVBoxLayout(self.WGT_LeftPane)

        # DURATION GRAPH
        self.LG_TimePerItem = pg.PlotWidget()
        x, y = self.getDurationData()
        self.CURVE_TimePerItem = self.LG_TimePerItem.plot(x, y)
        self.LG_TimePerItem.setTitle("Time per Item Over Batch Duration")
        self.LG_TimePerItem.setLabel('left', 'Duration', units='s')
        self.LG_TimePerItem.getAxis('bottom').enableAutoSIPrefix(False)
        self.LG_TimePerItem.getAxis('left').enableAutoSIPrefix(False)
        self.LG_TimePerItem.setLabel('bottom', 'Time Since Start', units='s', )
        self.LG_TimePerItem.showGrid(x=True, y=True)

        # Limit zoom/pan range
        self.VB_TimePerItem = self.LG_TimePerItem.getViewBox()

        xlim = max(x)
        ylim = max(y) * 1.2

        self.VB_TimePerItem.setLimits(
            xMin=0,
            xMax=xlim,
            yMin=0,
            yMax=ylim
        )
        # Size GRAPH
        self.LG_SizePerItem = pg.PlotWidget()
        x, y = self.getSizeData()
        self.CURVE_SizePerItem = self.LG_SizePerItem.plot(x, y)
        self.LG_SizePerItem.setTitle("Size Per Item")
        self.LG_SizePerItem.getAxis('bottom').enableAutoSIPrefix(False)
        self.LG_SizePerItem.getAxis('left').enableAutoSIPrefix(False)
        self.LG_SizePerItem.setLabel('left', 'Size', units='MB')
        self.LG_SizePerItem.setLabel('bottom', 'Time Since Start', units='s')
        self.LG_SizePerItem.showGrid(x=True, y=True)


        # Limit zoom/pan range
        self.VB_SizePerItem = self.LG_SizePerItem.getViewBox()
        xlim = max(x)
        ylim = max(y) * 1.2

        self.VB_SizePerItem.setLimits(
            xMin=0,
            xMax=xlim,
            yMin=0,
            yMax=ylim
        )

        self.VSTACK_LeftPane.addWidget(self.LG_TimePerItem)
        self.VSTACK_LeftPane.addWidget(self.LG_SizePerItem)

        
    # RIGHT PANE
        self.WGT_RightPane = QWidget()
        self.VSTACK_RightPane = QVBoxLayout(self.WGT_RightPane)

        # DURATION HISTOGRAM
        self.HIST_Duration = pg.PlotWidget()
        self.HIST_Duration.getPlotItem().setContentsMargins(15,15,15,15)
        self.HIST_Duration.setTitle("Item Durations")
        self.HIST_Duration.setLabel("left", "Count")
        self.HIST_Duration.setLabel("bottom", "Duration", units="s")

        counts, bins = self.getHistogramDurationData(self.BINS)
        
        self.HIST_LineDuration = pg.BarGraphItem(
            x=bins[:-1],
            height=counts,
            width=np.diff(bins),
        )
        self.HIST_Duration.addItem(self.HIST_LineDuration)
    
        self.VB_HistDuration = self.HIST_Duration.getViewBox()
        self.VB_HistDuration.setDefaultPadding(.5)
        self.VB_HistDuration.setLimits(xMin=0, yMin=0)
        
        # Size HISTOGRAM
        self.HIST_Size = pg.PlotWidget()
        self.HIST_Size.getPlotItem().setContentsMargins(15,15,15,15)
        self.HIST_Size.setTitle("Item Sizes")
        self.HIST_Size.setLabel("left", "Count")
        self.HIST_Size.setLabel("bottom", "Size", units="MB")
        self.HIST_Size.getAxis('bottom').enableAutoSIPrefix(False)
        self.HIST_Size.getAxis('left').enableAutoSIPrefix(False)

        counts, bins = self.getHistogramSizeData(self.BINS)
        
        self.HIST_LineSize = pg.BarGraphItem(
            x=bins[:-1],
            height=counts,
            width=np.diff(bins),
        )
        self.HIST_Size.addItem(self.HIST_LineSize)
    
        self.VB_HistSize = self.HIST_Size.getViewBox()
        self.VB_HistSize.setDefaultPadding(.5)
        self.VB_HistSize.setLimits(xMin=0, yMin=0)


        # PIE CHART
        self.PIE_Statuses = QChart()
        s = self.getSeries()
        self.PIE_Statuses.addSeries(s)
        self.PIE_Statuses.setTitle("Import Status Shares")
        self.PIE_Statuses.setTitleBrush(QColor("#969696"))
        self.PIE_Statuses.setBackgroundBrush(QColor("#000000"))
        self.PIE_Statuses.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self.PCV_Statuses = QChartView(self.PIE_Statuses)

        # PACKING
        self.VSTACK_RightPane.addWidget(self.HIST_Duration)
        self.VSTACK_RightPane.addWidget(self.HIST_Size)
        self.VSTACK_RightPane.addWidget(self.PCV_Statuses)
        self.VSTACK_RightPane.setStretch(0, 1)
        self.VSTACK_RightPane.setStretch(1, 1)
        self.VSTACK_RightPane.setStretch(2, 1)



        
    # PACKING CONTENTS
        self.GRID.addWidget(self.WGT_Header, 0, 0, 1, 2)
        self.GRID.addWidget(self.WGT_LeftPane, 1, 0)
        self.GRID.addWidget(self.WGT_RightPane, 1, 1)
        self.GRID.setColumnStretch(0, 3)
        self.GRID.setColumnStretch(1, 1)


    