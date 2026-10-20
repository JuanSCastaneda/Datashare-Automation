from Tabs.LastBatchTab import LastBatch
from Tabs.SummaryTab import SummaryTab
from Tabs.ConfigurationTab import ConfigurationTab
from Tabs.FailureSurveyTab import FailureSurvey
from Tabs.Dialogue import SettingsDialogue

from pathlib import Path
import sys
import logging 
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QTabWidget, QWidget, QDialog
)
import requests



class DashBoard(QWidget):
    def __init__(self, url: str, site_id: str):
        super().__init__()
        # APP
        self.URL = url
        self.SITE_ID = site_id
        # FEATURES
        self.TABS = QTabWidget()
        self.VLAYOUT = QVBoxLayout(self)

        # SETTING TITLE/ICON
        self.setWindowIcon(QIcon(r".\bin\src\mayahtt-thumbnail.png"))
        title = f"Datashare Automation | Site: {site_id.upper()}"
        response: dict[str, bool]= requests.get(self.URL).json()

        for k, v in response.items():
            title += f" | {k}: {"Active" if v else "Inactive"}"

        self.setWindowTitle(title)
    
        # CREATING TABS
       
        self.TAB_Summary = SummaryTab(url=self.URL)
        self.TAB_PerBatch = LastBatch(15, url=self.URL)
        self.TAB_FailureSurvey = FailureSurvey(url=self.URL)
        self.TAB_Confiuration = ConfigurationTab()


        # APPLYING TABS
        
        self.TABS.addTab(self.TAB_Summary, "Summary")
        self.TABS.addTab(self.TAB_PerBatch, "Per Batch")
        self.TABS.addTab(self.TAB_FailureSurvey, "Failure Survey")
        self.TABS.addTab(self.TAB_Confiuration, "Configuration")

        # ASSIGNING LAYOUT
        self.VLAYOUT.addWidget(self.TABS)      
        
        
        

def run():
    app = QApplication([])
    app_dir = Path(sys.argv[0]).resolve().parent
    stylesheet = app_dir / "Src" / "dark-theme.qss"

    dialogue = SettingsDialogue()
    dialogue.setWindowTitle("Consolidation Site Selection")
    dialogue.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
    dialogue.setWindowIcon(QIcon(r".\bin\src\mayahtt-thumbnail.png"))
    
    if dialogue.exec() != QDialog.DialogCode.Accepted:
        return
    

    # Getting Stylesheet
    
    app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
    
    siteID, server, port = dialogue.getParams()
    url = rf"http://{server}:{port}"


    # Test API
    try:
        requests.get(url)
    except requests.exceptions.ConnectionError:
        logging.info(f"API currently offline at {server}. Please check status.")
        return
    window = DashBoard(url, siteID)
    window.show()
    app.exec()
    


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')

    run()
