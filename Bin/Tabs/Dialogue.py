

from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QDialogButtonBox, QComboBox, QDialog
)
import json


class SettingsDialogue(QDialog):
    def accept(self):
        super().accept()

    def getParams(self):
        selected = self.COMBO_Sites.currentText()
        siteID = self.SITES[selected]['ID']
        url = self.SITES[selected]['URL']
        port = self.SITES[selected]['PortAPI']

        return siteID, url, port

    def __init__(self, configuration_file= r"Configuration\sites.json"):
        super().__init__()
        self.SELECTED = ''
        self.URL = ''
        self.PORT = ''


        self.VBOX = QVBoxLayout(self)
        self.LAB_Header = QLabel("Delare which site you are investigating")
        self.COMBO_Sites = QComboBox()
    
        with open(configuration_file, "r") as file:
            self.SITES: dict = json.load(file)

        for site in self.SITES.keys():
            self.COMBO_Sites.addItem(site)
        
        self.BUTTON = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.BUTTON.accepted.connect(self.accept)

        self.VBOX.addWidget(self.LAB_Header)
        self.VBOX.addWidget(self.COMBO_Sites)
        self.VBOX.addWidget(self.BUTTON)
        
