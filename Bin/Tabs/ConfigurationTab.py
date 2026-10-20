from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QComboBox, QLineEdit, QRadioButton
)

from pathlib import Path
import json
import sys

class ConfigurationTab(QWidget):
    def setConfigValues(self, configuration_file= r"Configuration\sites.json") -> None:

        # Extracting Configurations
        with open(configuration_file, "r") as file:
            data: dict = json.load(file)
        first = True

        if len(data) != 0:
            for site_id, param in data.items():
                self.COMBO_Sites.addItem(site_id)
                self.SITES[site_id] = param

                if first:
                    self.ENT_Name.setText(param["Name"])
                    self.ENT_ID.setText(param["ID"])
                    self.ENT_URL.setText(param["URL"])
                    self.ENT_Port.setText(param["PortAPI"])
                    first = False
    

    def saveConfiguration(self, configuration_file= r"Configuration\configuration.json") -> None:
        # Getting File Directory
        app_dir = Path(sys.argv[0]).resolve().parent
        path = app_dir / ".." / "Configuration" / "sites.json"

        name = self.ENT_Name.text()
        site_id = self.ENT_ID.text()
        url = self.ENT_URL.text()
        port = self.ENT_Port.text()

        if site_id not in self.SITES.keys():
            self.COMBO_Sites.addItem(site_id)
            
        self.SITES[site_id] = {
        "Name": name,
        "ID": site_id,
        "URL": url,
        "PortAPI": port
        }
        

        path.write_text(json.dumps(self.SITES, indent=2), encoding= "utf-8")


    def removeConfiguration(self,  configuration_file= r"Configuration\configuration.json"):
        # Getting File Directory
        app_dir = Path(sys.argv[0]).resolve().parent
        path = app_dir / ".." / "Configuration" / "sites.json"

        
        site_id = self.COMBO_Sites.currentText()


        if site_id in self.SITES.keys():
            index = self.COMBO_Sites.findText(site_id)
            self.COMBO_Sites.removeItem(index)
            
        self.SITES.pop(site_id)

        path.write_text(json.dumps(self.SITES, indent=2), encoding= "utf-8")
        
        
    def comboChanged(self):
        param  = self.SITES[self.COMBO_Sites.currentText()]
        self.ENT_Name.setText(param["Name"])
        self.ENT_ID.setText(param["ID"])
        self.ENT_URL.setText(param["URL"])
        self.ENT_Port.setText(param["PortAPI"])

    def __init__(self):
        super().__init__()

    # GRID LAYOUT
        self.SITES = dict()
        self.GRID = QGridLayout(self)

    # FEATURES
        # PATH TO TEAMCENTER BATCH
        self.LAB_Sites = QLabel("Site Declaration")
        self.LAB_Sites.setObjectName('subheader')
        self.LAB_Combo = QLabel("Sites")

        self.LAB_Name = QLabel("Site Name:")
        self.ENT_Name = QLineEdit()
        self.ENT_Name.setPlaceholderText("e.g. Luxembourg Dev")
        self.LAB_ID = QLabel("Site ID")
        self.ENT_ID = QLineEdit()
        self.ENT_ID.setPlaceholderText("lxdev10")
        self.LAB_URL = QLabel("URL:")
        self.ENT_URL = QLineEdit()
        self.ENT_URL.setPlaceholderText("lududsvdtc1002")
        self.LAB_Port = QLabel("API Port:")
        self.ENT_Port = QLineEdit()
        self.ENT_Port.setText("8000")

        self.COMBO_Sites = QComboBox()
       


        self.BUT_Save = QPushButton("Save")
        self.BUT_Save.clicked.connect(self.saveConfiguration)

        self.BUT_Remove = QPushButton("Remove")
        self.BUT_Remove.clicked.connect(self.removeConfiguration)


        self.GRID.addWidget(self.LAB_Sites, 0,0,1,2)
        self.GRID.addWidget(self.LAB_Combo, 1, 0)
        self.GRID.addWidget(self.COMBO_Sites, 1, 1)
        self.GRID.addWidget(self.BUT_Remove, 2, 1)
        self.GRID.addWidget(QLabel(), 3, 0 )

        
        self.GRID.addWidget(self.LAB_Name, 4, 0)
        self.GRID.addWidget(self.ENT_Name, 4, 1)
        self.GRID.addWidget(self.LAB_ID, 5, 0)
        self.GRID.addWidget(self.ENT_ID, 5, 1)
        
        self.GRID.addWidget(self.LAB_URL, 6, 0)
        self.GRID.addWidget(self.ENT_URL, 6, 1)
        self.GRID.addWidget(self.LAB_Port, 7, 0)
        self.GRID.addWidget(self.ENT_Port, 7, 1)
        self.GRID.addWidget(self.BUT_Save, 8, 0,1,2)
        
        self.GRID.setColumnStretch(0, 1)
        self.GRID.setColumnStretch(1, 4)
        self.GRID.setRowStretch(3, 3)
        # SAVE
        self.setConfigValues()
        self.COMBO_Sites.currentIndexChanged.connect(self.comboChanged)
    
    

