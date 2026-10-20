from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QPushButton, QVBoxLayout, QLineEdit, QRadioButton
)

from pathlib import Path
import json
import sys

class ConfigurationTab(QWidget):
    def setConfigValues(self, configuration_file= r"Configuration\configuration.json") -> None:

        # Extracting Configurations
        with open(configuration_file, "r") as file:
            data = json.load(file)
        

        self.ENT_TcPath.setText(data['TeamcenterBat'])
        self.ENT_source_site.setText(data['SourceSiteName'])
        self.ENT_target_site.setText(data['TargetSiteName'])
        self.ENT_database_name.setText(data['SQLiteDatabaseName'])

        if data['Oracle'] == True:
            self.RAD_Oracle.setChecked(True)
            self.ENT_OracleUser.setText(data['OracleUser'])
            self.ENT_OraclePassword.setText(data['OraclePassword'])
            self.ENT_Host.setText(data['OracleHost'])
            self.ENT_Port.setText(data['OraclePort'])
            self.ENT_ServiceName.setText(data['OracleService'])
        
        # DEV NOTES: ADD MSSQL CONFIG LATER


    def saveConfiguration(self, configuration_file= r"Configuration\configuration.json") -> None:
        # Getting File Directory
        app_dir = Path(sys.argv[0]).resolve().parent
        path = app_dir / ".." / "Configuration" / "configuration.json"

        data = dict()

        data['TeamcenterBat'] = self.ENT_TcPath.text()
        data['SourceSiteName'] = self.ENT_source_site.text()
        data['TargetSiteName'] = self.ENT_target_site.text()
        data['SQLiteDatabaseName'] = self.ENT_database_name.text()
        data['Oracle'] = True if self.RAD_Oracle.isChecked() == True else False
        data['OracleUser'] = self.ENT_OracleUser.text()
        data['OraclePassword'] = self.ENT_OraclePassword.text()
        data['OracleHost'] = self.ENT_Host.text()
        data['OraclePort'] = self.ENT_Port.text()
        data['OracleService'] = self.ENT_ServiceName.text()
        data['ApiPort'] = 8000

        path.write_text(json.dumps(data, indent=2), encoding= "utf-8")

        batchPath = app_dir / ".." / "DatashareDashboard.bat"
        vEnvPath = app_dir / ".." / "MVenv" / "Scripts" / "activate.bat"
        mainPath = app_dir / ".." / "Main.py"
        batchPath.write_text(f"""
            call "{data['TeamcenterBat']}"
            call "{vEnvPath}"
            {mainPath}
                         """.replace('\t', ''))
        


    def __init__(self):
        super().__init__()

    # GRID LAYOUT
        self.VSTACK_Sections = QVBoxLayout(self)

    # FEATURES
        # PATH TO TEAMCENTER BATCH
        self.WGT_TcConfigs = QWidget()
        self.GRID_Tc_configs_heading = QGridLayout(self.WGT_TcConfigs)
        self.LAB_Tc_configs_heading = QLabel("Teamcenter Configuation")
        self.LAB_Tc_configs_heading.setObjectName('subheader')

        self.LAB_TcPath = QLabel("Path to Teamcenter Command Prompt")
        self.ENT_TcPath = QLineEdit()
        self.ENT_TcPath.setPlaceholderText("Restart Application When Changed")

        self.GRID_Tc_configs_heading.addWidget(self.LAB_Tc_configs_heading, 0, 0, 1, 2)
        self.GRID_Tc_configs_heading.addWidget(self.LAB_TcPath, 1, 0)
        self.GRID_Tc_configs_heading.addWidget(self.ENT_TcPath, 1, 1)

        # DATASHARE CONFIGS SECTION
        self.WGT_DatashareConfigs = QWidget()
        self.GRID_datashare_configs = QGridLayout(self.WGT_DatashareConfigs)
        self.LAB_datashare_configs_heading = QLabel("Datashare Configs")
        self.LAB_datashare_configs_heading.setObjectName('subheader')

        self.LAB_source_site = QLabel("Source Site")
        self.ENT_source_site = QLineEdit()

        self.LAB_target_site = QLabel("Target Site")
        self.ENT_target_site = QLineEdit()

        self.LAB_database_name = QLabel("Database File Name (.db)")
        self.ENT_database_name = QLineEdit()

        self.GRID_datashare_configs.addWidget(self.LAB_datashare_configs_heading, 0, 0, 1, 2)
        self.GRID_datashare_configs.addWidget(self.LAB_TcPath, 1, 0)
        self.GRID_datashare_configs.addWidget(self.ENT_TcPath, 1, 1)
        self.GRID_datashare_configs.addWidget(self.LAB_source_site, 2, 0)
        self.GRID_datashare_configs.addWidget(self.ENT_source_site, 2, 1)
        self.GRID_datashare_configs.addWidget(self.LAB_target_site, 3, 0)
        self.GRID_datashare_configs.addWidget(self.ENT_target_site, 3, 1)
        self.GRID_datashare_configs.addWidget(self.LAB_database_name, 4, 0)
        self.GRID_datashare_configs.addWidget(self.ENT_database_name, 4, 1)


        # DATABASE MANAGEMENT SYSTEM SECTION
        self.WGT_DatabaseMgtConfig = QWidget()
        self.GRID_DatabaseMgtConfig = QGridLayout(self.WGT_DatabaseMgtConfig)

        # Oracle
        self.LAB_MgtSystem = QLabel("Database Management System")
        self.LAB_MgtSystem.setObjectName('subheader')
        self.RAD_Oracle = QRadioButton("Oracle")

        self.LAB_OracleUser = QLabel("User")
        self.ENT_OracleUser = QLineEdit()

        self.LAB_OraclePassword = QLabel("Password")
        self.ENT_OraclePassword = QLineEdit()
        self.ENT_OraclePassword.setEchoMode(QLineEdit.EchoMode.Password)

        self.LAB_Host = QLabel("Database Host")
        self.ENT_Host = QLineEdit()

        self.LAB_Port = QLabel("Database Port")
        self.ENT_Port = QLineEdit()

        self.LAB_ServiceName = QLabel("Service Name")
        self.ENT_ServiceName = QLineEdit()

        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_MgtSystem, 0, 0, 1, 4)
        self.GRID_DatabaseMgtConfig.addWidget(self.RAD_Oracle, 1, 0, 1, 2)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_OracleUser, 2, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_OracleUser, 2, 1)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_OracleUser, 3, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_OracleUser, 3, 1)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_OraclePassword, 4, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_OraclePassword, 4, 1)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_Host, 5, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_Host, 5, 1)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_Port, 6, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_Port, 6, 1)
        self.GRID_DatabaseMgtConfig.addWidget(self.LAB_ServiceName, 7, 0)
        self.GRID_DatabaseMgtConfig.addWidget(self.ENT_ServiceName, 7, 1)

        # SAVE
        self.BUT_Save = QPushButton("Save")
        self.BUT_Save.clicked.connect(self.saveConfiguration)


    # PACKING SECTIONS
        self.VSTACK_Sections.addWidget(self.WGT_TcConfigs)
        self.VSTACK_Sections.addWidget(self.WGT_DatashareConfigs)
        self.VSTACK_Sections.addWidget(self.WGT_DatabaseMgtConfig)
        self.VSTACK_Sections.addWidget(self.BUT_Save)
        self.setConfigValues()

    
    

