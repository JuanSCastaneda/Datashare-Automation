from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QCheckBox, QComboBox, QRadioButton, QVBoxLayout 
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtCharts import (
    QChart, QPieSeries, QChartView     
)
from BatchResult.BatchResult import BatchResults
from BatchResult.BatchesHistogram import BatchHistogram
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
import requests

class SummaryTab(QWidget):
    def radioWasChanged(self):
        if self.RAD_AllData.isChecked():
            self.COMBO_RollingAvg.setEnabled(False)
            
            
        elif self.RAD_RollingAvg.isChecked():
            self.COMBO_RollingAvg.setEnabled(True)

        self.updateTPIGraph()
        
    def updateSummaryMetrics(self) -> None:
        if self.RAD_AllData.isChecked():
            self.LAB_AccountingFor.setText("Using All Data")
        elif self.RAD_RollingAvg.isChecked():
            self.LAB_AccountingFor.setText(f"Using The Last {self.COMBO_RollingAvg.currentText()} Batches")
        
        if self.CHK_OutlierRemoval.isChecked():
            self.LAB_OutlierRemoval.setText("With Outliers Removed")
        else:
            self.LAB_OutlierRemoval.setText("")
        
        self.LAB_AverageSpeed.setText(f"Average Speed: {np.round(self.AvgSpeed, 2)} Seconds/Item")

        now = datetime.now()
        endDateUnproc = now + timedelta(seconds= (self.AvgSpeed  * self.NULL))
        endDateUnprocFailed = now + timedelta(seconds= (self.AvgSpeed * (self.NULL + self.FAILED)))
        self.LAB_TimeRemainingUnprocessed.setText(f"End Date for Unprocessed Items: {endDateUnproc.strftime('%B %d %Y')}")
        self.LAB_TimeRemainingFailUnproc.setText(f"End Date for Failed & Unprocessed Items: {endDateUnprocFailed.strftime('%B %d %Y')} ")   

    def getGraphingParameters(self):
        if self.RAD_RollingAvg.isChecked():
            rolling_avg_input = True
            try:
                rolling_avg_limit_input = int(self.COMBO_RollingAvg.currentText())
            
            except ValueError:
                print(f"There was an error converting '{self.COMBO_RollingAvg.currentText()}' to an int")
        else:
            rolling_avg_input = False
            rolling_avg_limit_input = 0

        remove_outlier_Input = True if self.CHK_OutlierRemoval.isChecked() else False

        return remove_outlier_Input, rolling_avg_input, rolling_avg_limit_input
    

    def updateTPIGraph(self):
        configs = self.getGraphingParameters()
        new_x, new_y = self.BATCHES.preProcessTimePerItem(*configs)
        self.LG_TimePerItem.removeItem(self.LG_TimePerItemCurve)
        self.LG_TimePerItemCurve = (self.LG_TimePerItem.plot(new_x, new_y))
        self.TPI_vb.setLimits(xMin=min(new_x), xMax=max(new_x), yMin=0, yMax=max(new_y)*1.25)

        self.AvgSpeed = np.mean(new_y)      # Setting New Average Speed
        
        if self.RAD_UsingSpeed.isChecked():
            self.updateSummaryMetrics()         # Updating Metrics


    def getPieSeries(self) -> QPieSeries:
        data = requests.get(f"{self.URL}/summary").json()
        nSuccess = data['SUCCESSFUL']
        nFailed = data['FAILED']
        nNull = data['NULL']
        nSkipped = data['SKIPPED']


        series = QPieSeries()
        series.append("Pass", nSuccess)
        series.append("Fail", nFailed)
        # series.append("Skip", nSkipped)
        series.append("Awaiting", nNull)


        try: 
            nInconsistent = data['INCONSISTENT SITE OWNERSHIP']
            series.append("Mixed", nInconsistent)
            
        except KeyError:
            pass
        
        # try: 
        #     nOther = data['OTHER']
        #     series.append("Other", nOther)
            
        # except KeyError:   
        #     pass
            

        self.SUCCESSFUL = nSuccess
        self.FAILED = nFailed
        self.SKIPPED = nSkipped
        self.NULL = nNull
        # n = nSuccess + nFailed + nNull

        # labelColors = [("Succesful", '#ff4600'),("Failed", '#ff8D64'), ("Skipped", '#fff3ef'), ("Unprocessed", '#ffcdba')]
        # explodeFirst = True
        # for s_, labelColor in zip(series.slices(), labelColors):
        #     if explodeFirst:
        #         s_.setExploded(True)
        #         s_.setExplodeDistanceFactor(.15)
        #         explodeFirst = False
        #     s_.setLabel(f"{labelColor[0]} {(s_.value() / n * 100):.1f}%")
        #     s_.setBrush(QColor(labelColor[1]))
        #     s_.setLabelColor(QColor("#969696"))
        #     s_.setLabelBrush(QColor("#969696"))

        return series
    

    def getNThroughputPoints(self, N):
        x, y = self.CURVE_DailyThroughput.getData()
        sample = y[-N-1:-1]

        return (np.average(sample), np.max(sample), np.min(sample))


    def changedEstimateMode(self):

        if self.RAD_UsingDTP.isChecked():
            self.CHK_OutlierRemoval.setVisible(False)
            self.WGT_Throughput.setVisible(True)
            self.WGT_Speed.setVisible(False)

            self.COMBO_NThreads.setVisible(False)
            self.LAB_NThreads.setVisible(False)
            self.COMBO_TPWindow.setVisible(True)
            self.LAB_LastNDaysTP.setVisible(True)

            self.changedNPTDays()
        
        elif self.RAD_UsingSpeed.isChecked():
            self.CHK_OutlierRemoval.setVisible(True)
            self.WGT_Throughput.setVisible(False)
            self.WGT_Speed.setVisible(True)

            self.COMBO_NThreads.setVisible(True)
            self.LAB_NThreads.setVisible(True)
            self.COMBO_TPWindow.setVisible(False)
            self.LAB_LastNDaysTP.setVisible(False)

            self.changedNThreads()

    def changedNPTDays(self):
        
        self.averageTP, self.maximumTP, self.minimumTP = self.getNThroughputPoints(int(self.COMBO_TPWindow.currentText()))
        endDateUnproc = self.now + timedelta(days= (self.NULL / self.averageTP))
        endDateUnprocFailed = self.now + timedelta(days= ((self.NULL + self.FAILED) / self.averageTP))

        self.LAB_AverageTP.setText(f"Average TP: {int(self.averageTP)}")
        self.LAB_MaxTP.setText(f"Maximum TP: {int(self.maximumTP)}")
        self.LAB_MinTP.setText(f"Minimum TP: {int(self.minimumTP)}")


        self.LAB_TimeRemainingUnprocessed.setText(f"End Date for Unprocessed Items: {endDateUnproc.strftime('%B %d %Y')}")
        self.LAB_TimeRemainingFailUnproc.setText(f"End Date for Failed & Unprocessed Items: {endDateUnprocFailed.strftime('%B %d %Y')} ")  

        
    
    def changedNThreads(self):
        endDateUnproc = self.now + timedelta(seconds= (self.NULL * self.AvgSpeed / int(self.COMBO_NThreads.currentText())))
        endDateUnprocFailed = self.now + timedelta(seconds= ((self.NULL + self.FAILED) * self.AvgSpeed / int(self.COMBO_NThreads.currentText())))

        self.LAB_TimeRemainingUnprocessed.setText(f"End Date for Unprocessed Items: {endDateUnproc.strftime('%B %d %Y')}")
        self.LAB_TimeRemainingFailUnproc.setText(f"End Date for Failed & Unprocessed Items: {endDateUnprocFailed.strftime('%B %d %Y')} ")  

    def __init__(self, url: str = r"http://127.0.0.1:8000"):
        super().__init__()
        self.URL = url
        self.GRID = QGridLayout(self)
        self.SUCCESSFUL: int
        self.FAILED: int
        self.SKIPPED: int
        self.NULL: int
        self.AvgSpeed: float

    # FEATURES
    # SETTING SELECTION
        self.WGT_Settings = QWidget()
        self.GRID_Settings = QGridLayout(self.WGT_Settings)
        
        self.LAB_Header = QLabel("Transfer Summary")
        self.LAB_Header.setObjectName("header")
        self.LAB_SpeedSwitches = QLabel("Speed Options")
        self.LAB_SpeedSwitches.setObjectName("subheader")

        
        self.RAD_AllData = QRadioButton("All Data")
        self.RAD_AllData.setChecked(True)
        self.RAD_AllData.clicked.connect(self.radioWasChanged)
        self.RAD_RollingAvg = QRadioButton("Rolling Average")
        self.RAD_RollingAvg.clicked.connect(self.radioWasChanged)

        self.CHK_OutlierRemoval = QCheckBox("Outlier Removal")
        self.CHK_OutlierRemoval.clicked.connect(self.updateTPIGraph)
        self.COMBO_RollingAvg = QComboBox()
        self.COMBO_RollingAvg.addItems([str(i) for i in range(25, 525, 25)])
        self.COMBO_RollingAvg.setCurrentText('10')
        self.COMBO_RollingAvg.setEnabled(False)
        self.COMBO_RollingAvg.currentTextChanged.connect(self.updateTPIGraph)
        

        self.GRID_Settings.addWidget(self.LAB_Header, 0, 0, 1, 3)
        self.GRID_Settings.addWidget(self.LAB_SpeedSwitches, 1, 0)
        self.GRID_Settings.addWidget(self.RAD_AllData, 1, 1)
        self.GRID_Settings.addWidget(self.RAD_RollingAvg, 1, 2)
        self.GRID_Settings.addWidget(self.CHK_OutlierRemoval, 1, 3)
        self.CHK_OutlierRemoval.setVisible(False)
        self.GRID_Settings.addWidget(self.COMBO_RollingAvg, 1, 4, 1, 2)
        

    # LEFT GRAPH PANELS
        self.WGT_LeftPanel = QWidget()
        self.VSTACK_LeftPanel = QVBoxLayout(self.WGT_LeftPanel)
        
        self.BATCHES = BatchResults(url=self.URL)
       
        # DAILY THROUGHPUT 
        x1, y1 = self.BATCHES.preProcessDailyThroughput()
        self.LG_DailyThroughput = pg.PlotWidget()
        self.LG_DailyThroughput.getPlotItem().setContentsMargins(15,15,15,15)
        self.CURVE_DailyThroughput = self.LG_DailyThroughput.plot(x1, y1)
        self.LG_DailyThroughput.showGrid(x=True, y=True)
        self.LG_DailyThroughput.setTitle("Daily Item Throughput")
        self.LG_DailyThroughput.setLabel('left','Items Per Day')
        self.LG_DailyThroughput.setLabel('bottom', 'Days Since Start', units='Days')

        # Limit zoom/pan range
        DTP_vb = self.LG_DailyThroughput.getViewBox()
        DTP_vb.setLimits(xMin=min(x1), xMax=max(x1), yMin=0, yMax=max(y1)*1.25)
        DTP_vb.setDefaultPadding(.1)
        self.VSTACK_LeftPanel.addWidget(self.LG_DailyThroughput)

        # TIME PER ITEM
        clean, rollingAvg, rollingAvgLim = self.getGraphingParameters()
        x2, y2 = self.BATCHES.preProcessTimePerItem(clean, rollingAvg, rollingAvgLim)
        self.AvgSpeed = np.mean(y2)
        self.LG_TimePerItem = pg.PlotWidget()
        self.LG_TimePerItem.getPlotItem().setContentsMargins(15,15,15,15)
        self.LG_TimePerItem.showGrid(x=True, y=True)
        self.LG_TimePerItemCurve = self.LG_TimePerItem.plot(x2, y2)
        self.LG_TimePerItem.setTitle("Transfer Time Per Item")
        self.LG_TimePerItem.setLabel('left','Time', units='s')
        self.LG_TimePerItem.setLabel('bottom', 'Batch Index')

        # Limit zoom/pan range
        self.TPI_vb = self.LG_TimePerItem.getViewBox()
        self.TPI_vb.setLimits(xMin=min(x2), xMax=max(x2), yMin=0, yMax=max(y2)*1.25)
        self.TPI_vb.setDefaultPadding(.5)
        self.VSTACK_LeftPanel.addWidget(self.LG_TimePerItem)


        
    # RIGHT PANE SUMMARY
        # SIZE EFFICICENT HISTOGRAM
        self.WGT_RightPanel = QWidget()
        self.VSTACK_RightPanel = QVBoxLayout(self.WGT_RightPanel)

        self.HIST_BatchSizes = pg.PlotWidget()
        self.HIST_BatchSizes.getPlotItem().setContentsMargins(15,15,15,15)
        self.HIST_BatchSizes.setTitle("Batch Size Efficiency")
        self.HIST_BatchSizes.setLabel("left", "Count")
        self.HIST_BatchSizes.setLabel("bottom", "Batch Size")
        self.HIST_Legend = self.HIST_BatchSizes.addLegend(offset=(-10,10))

        hists = self.BATCHES.preProcessHistorgram(bins=50)
        
        m = len(hists)
        cmap = pg.colormap.get('viridis')       
        colors = [cmap.map(i, mode='qcolor') for i in np.linspace(0, 1, m)]

        for i, hist in enumerate(hists):
            line = pg.BarGraphItem(
                x=hist.BINS[:-1],
                height=hist.COUNTS,
                width=np.diff(hist.BINS),
                pen=colors[i]
            )
            self.HIST_BatchSizes.addItem(line)
            self.HIST_Legend.addItem(line, f"{hist.SIZE}: \u00B5={np.round(hist.MEAN, 2)} \u03C3={np.round(hist.STD,2)}, #: {len(hist.DURATIONS)}")

        HIST_vb = self.HIST_BatchSizes.getViewBox()
        HIST_vb.setLimits(xMin=0, yMin=0, xMax=15)
        HIST_vb.setDefaultPadding(.5)

        # REMAINING PIE CHART METRICS
        series = self.getPieSeries()
        series.setLabelsVisible(True)

        self.PIE_Chart = QChart()
        self.PIE_Chart.addSeries(series)
        self.PIE_Chart.setTitle("Summary of Remaining")
        self.PIE_Chart.setTitleBrush(QColor("#969696"))
        self.PIE_Chart.setBackgroundBrush(QColor("#000000"))
        self.PIE_Chart.legend().setVisible(True)
        self.PIE_Chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self.PIE_ChartView = QChartView(self.PIE_Chart)


        # METRICS WIDGET
        self.WGT_Metrics = QWidget()
        self.GRID_Metrics = QGridLayout(self.WGT_Metrics)

        # How Calculated Widget
        # ------------------------------------------------------------------------
        self.WGT_HowCalculated = QWidget()
        self.GRID_HowCalculated = QGridLayout(self.WGT_HowCalculated)

        self.RAD_UsingSpeed = QRadioButton("Using Speed")
        self.RAD_UsingDTP = QRadioButton("Using Daily Throughput")
        self.RAD_UsingDTP.setChecked(True)
        self.GRID_HowCalculated.addWidget(self.RAD_UsingSpeed, 0, 0)
        self.GRID_HowCalculated.addWidget(self.RAD_UsingDTP, 0, 1)

        self.RAD_UsingSpeed.toggled.connect(self.changedEstimateMode)
        self.RAD_UsingDTP.toggled.connect(self.changedEstimateMode)

        # Items Remaining Widget
        # ------------------------------------------------------------------------
        self.WGT_ItemsRemaining = QWidget()
        self.GRID_ItemsRemaining = QGridLayout(self.WGT_ItemsRemaining)

        self.LAB_ItemsRemainingHeader = QLabel("Items Remaining")
        self.LAB_ItemsRemainingHeader.setObjectName('subheader')
        self.LAB_Successful = QLabel(f"# Succesful Items: {self.SUCCESSFUL:,d}")
        self.LAB_Failed = QLabel(f"# Failed Items: {self.FAILED:,d}")
        self.LAB_Skipped = QLabel(f"# Skipped Items: {self.SKIPPED:,d}")
        self.LAB_Null = QLabel(f"# Unprocessed Items: {self.NULL:,d}")

        self.GRID_ItemsRemaining.addWidget(self.LAB_ItemsRemainingHeader, 0, 0)
        self.GRID_ItemsRemaining.addWidget(self.LAB_Successful, 1, 0)
        self.GRID_ItemsRemaining.addWidget(self.LAB_Failed, 2, 0)
        self.GRID_ItemsRemaining.addWidget(self.LAB_Skipped, 3, 0)
        self.GRID_ItemsRemaining.addWidget(self.LAB_Null, 4, 0)


        # Speed Widget
        # ------------------------------------------------------------------------
        self.WGT_Speed = QWidget()
        self.GRID_Speed = QGridLayout(self.WGT_Speed)
        
        self.LAB_SpeedHeader = QLabel("Speed")
        self.LAB_SpeedHeader.setObjectName('subheader')
        self.LAB_AccountingFor = QLabel("Using All Data")
        self.LAB_OutlierRemoval = QLabel("")
        self.LAB_AverageSpeed = QLabel(f"Average Speed: {np.round(self.AvgSpeed, 2)} Seconds/Item")
        
        self.GRID_Speed.addWidget(self.LAB_SpeedHeader, 0, 0)
        self.GRID_Speed.addWidget(self.LAB_AccountingFor, 1, 0)
        self.GRID_Speed.addWidget(self.LAB_OutlierRemoval, 2, 0)
        self.GRID_Speed.addWidget(self.LAB_AverageSpeed, 3, 0)

        self.LAB_NThreads = QLabel("#Threads")
        self.COMBO_NThreads = QComboBox()
        self.COMBO_NThreads.addItems([str(i) for i in range(1, 5)])
        self.COMBO_NThreads.setCurrentText('1')
        self.COMBO_NThreads.currentTextChanged.connect(self.changedNThreads)


        # Throughput Widget
        # ------------------------------------------------------------------------
        self.WGT_Throughput = QWidget()
        self.GRID_Throughput = QGridLayout(self.WGT_Throughput)

        N_MAX = 14
        
        self.LAB_TPHeader = QLabel("Daily Throughput")
        self.LAB_TPHeader.setObjectName("subheader")

        

        self.LAB_LastNDaysTP = QLabel(f"#Days")
        self.COMBO_TPWindow = QComboBox()
        self.COMBO_TPWindow.addItems([str(i) for i in range(1, N_MAX + 1)])
        self.COMBO_TPWindow.setCurrentText('7')
        self.COMBO_TPWindow.currentTextChanged.connect(self.changedNPTDays)

        self.averageTP, self.maximumTP, self.minimumTP = self.getNThroughputPoints(int(self.COMBO_TPWindow.currentText()))
        self.LAB_AverageTP = QLabel(f"Average TP: {int(self.averageTP)}")
        self.LAB_MaxTP = QLabel(f"Maximum TP: {int(self.maximumTP)}")
        self.LAB_MinTP = QLabel(f"Minimum TP: {int(self.minimumTP)}")

        self.GRID_Throughput.addWidget(self.LAB_TPHeader, 0, 0, 1, 1)
        self.GRID_Throughput.addWidget(self.LAB_AverageTP, 1, 0)
        self.GRID_Throughput.addWidget(self.LAB_MaxTP, 2, 0)
        self.GRID_Throughput.addWidget(self.LAB_MinTP, 3, 0)
        


        # Time Remaining Widget
        # ------------------------------------------------------------------------
        self.WGT_TimeRemaining = QWidget()
        self.GRID_TimeRemaining = QGridLayout(self.WGT_TimeRemaining)

        self.LAB_TimeRemainingHeader = QLabel("Time Remaining")
        self.LAB_TimeRemainingHeader.setObjectName('subheader')
        self.now = datetime.now()

        endDateUnproc = self.now + timedelta(days= (self.NULL / self.averageTP))
        endDateUnprocFailed = self.now + timedelta(days= ((self.NULL + self.FAILED) / self.averageTP))

        self.LAB_TimeRemainingUnprocessed = QLabel(f"End Date for Unprocessed Items: {endDateUnproc.strftime('%B %d %Y')}")
        self.LAB_TimeRemainingFailUnproc = QLabel(f"End Date for Failed & Unprocessed Items: {endDateUnprocFailed.strftime('%B %d %Y')} ")   

        self.GRID_TimeRemaining.addWidget(self.LAB_TimeRemainingHeader, 0,0)
        self.GRID_TimeRemaining.addWidget(self.LAB_LastNDaysTP,0,1)
        self.GRID_TimeRemaining.addWidget(self.LAB_TimeRemainingUnprocessed, 1,0)
        self.GRID_TimeRemaining.addWidget(self.LAB_TimeRemainingFailUnproc, 2,0)


        # nThreads
        self.GRID_TimeRemaining.addWidget(self.LAB_NThreads,0,1)
        self.GRID_TimeRemaining.addWidget(self.COMBO_NThreads, 1, 1, 2, 1)
        self.LAB_NThreads.setVisible(False)
        self.COMBO_NThreads.setVisible(False)
        # nDays
        self.GRID_TimeRemaining.addWidget(self.LAB_LastNDaysTP,0,1)
        self.GRID_TimeRemaining.addWidget(self.COMBO_TPWindow, 1, 1, 2, 1)
        

        self.GRID_TimeRemaining.setColumnStretch(0,4)
        self.GRID_TimeRemaining.setColumnStretch(1,1)


        # PACKING METRICS
        # ------------------------------------------------------------------------

        self.GRID_Metrics.addWidget(self.WGT_HowCalculated, 0, 0, 1, 2)
        self.GRID_Metrics.addWidget(self.WGT_ItemsRemaining, 1, 0)
        self.GRID_Metrics.addWidget(self.WGT_Speed, 1, 1)
        self.WGT_Speed.setVisible(False)
        self.GRID_Metrics.addWidget(self.WGT_Throughput, 1, 1)
        self.GRID_Metrics.addWidget(self.WGT_TimeRemaining, 2, 0, 1, 2)
  


        # PACKING
        self.VSTACK_RightPanel.addWidget(self.HIST_BatchSizes, stretch= 2)
        self.VSTACK_RightPanel.addWidget(self.PIE_ChartView, stretch= 3)
        self.VSTACK_RightPanel.addWidget(self.WGT_Metrics, stretch= 1)


    # PACKING PAGE
        self.GRID.addWidget(self.WGT_Settings, 0, 0, 1, 2)
        self.GRID.addWidget(self.WGT_LeftPanel, 1, 0)
        self.GRID.addWidget(self.WGT_RightPanel, 1, 1)
        self.GRID.setColumnStretch(0,3)
        self.GRID.setColumnStretch(1,1)



