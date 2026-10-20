import xml.etree.ElementTree as ET
import logging
import subprocess
import json
from .Exceptions import *
from shutil import move
import os
from pathlib import Path

class UpgradePreChecker:
    def __init__(self, staging_dir: str = "E:\\plmapps\\MayaConfig", configuration_file: str="Configuration\\configuration.json", u=None, p=None):
        try:
            self.MIG_HOME = migHome = os.environ['MIG_HOME']
            self.configurationFile = f"{self.MIG_HOME}\\{configuration_file}"

        except:
            logging.warning(f"Could not find MIG_HOME in Environment Variables. Defaulting to local directory.")
            self.MIG_HOME = None
            self.configurationFile = configuration_file

        with open(configuration_file, "r") as file:
            data = json.load(file)

        # DATABASE MANAGEMENT SYSTEM VARIABLES


        # DATASHARE CONFIGURATIONS
        self.server: str = data['SourceSiteName']
        self.u = data['OracleUser'] if u is None else u
        self.p = data['OraclePassword'] if p is None else p

        self.stagingDir = staging_dir + "PreUpgradeChecks" if staging_dir[-1] == "\\" else staging_dir + "\\PreUpgradeChecks"
        if not Path(self.stagingDir).exists():
            os.mkdir(self.stagingDir)

    def exportAdminData(self) -> None:
        """
        Calls
            1. Generates backup.xml
            2. Exports preferences
            3. Exports Organization
            
        """
        # self.exportAccessManager()
        self.exportPreferences()
        self.exportBackup()
        self.exportMissingIndices()
        self.exportOrganization()
        
        
        
    # EXPORTERS   
    # ======================================================================================================================
    def exportAccessManager(self):
        try:
            logging.info("Exporting Access Manager Tree...")
            if not Path(f"{self.stagingDir}\\AccessManager.xml").exists():
                subprocess.run(["cmd", "/c", "am_install_tree", f"-u={self.u}", f"-p={self.p}", "-g=dba", "-operation=export", f"-path={self.stagingDir}\\AccessManager.xml", "-format=xml"],
                                text=True)

                logging.info("Sucessfully exported Access Manager Tree...")
            
            else:
                logging.info("AM already exported...")

        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
            raise MissingTeamcenterMethod("Missing am_install_tree method, please ensure that the teamcenter bat is well defined in UpgradeChecks.bat")
        

    def exportPreferences(self) -> None:
        try:
            logging.info("Exporting Preferences...")
            subprocess.run(["cmd", "/c", "preferences_manager", f"-u={self.u}", f"-p={self.p}", "-g=dba", "-scope=SITE", "-mode=export",
                            f"-out_file={self.stagingDir}\\preferences.xml"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
            raise MissingTeamcenterMethod("Missing preference_manager method, please ensure that the teamcenter bat is well defined in UpgradeChecks.bat")
        

    def exportBackup(self) -> None:
        try:
            logging.info("Exporting backup.xml...")
            subprocess.run(["cmd", "/c", "backup_xmlinfo", f"-u={self.u}", f"-p={self.p}", "-g=dba"], check=True)
            move(".\\backup.xml", f"{self.stagingDir}\\backup.xml")
            move(".\\backup.dtd", f"{self.stagingDir}\\backup.dtd")

            logging.info("Successfully generated backup.xml")

        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
            raise MissingTeamcenterMethod("Missing backup_xmlinfo method, please ensure that the teamcenter bat is well defined in UpgradeChecks.bat")
        
    
    def exportOrganization(self) -> None:
        try:
            logging.info("Exporting Organization...")
            subprocess.run(["cmd", "/c", "plmxml_export", f"-u={self.u}", f"-p={self.p}", "-g=dba",
                                        f"-xml_file={self.stagingDir}\\organization.xml", "-class=Group"], check=True)
            logging.info("Sucessfully wrote organization.xml")
        
        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
            raise MissingTeamcenterMethod("Missing plmxml_export method, please ensure that the teamcenter bat is well defined in UpgradeChecks.bat")
    
    def exportMissingIndices(self):
        try: 
            logging.info("Writting missing indices file...")
            subprocess.run(["cmd", "/c", "index_verifier", f"-u={self.u}", f"-p={self.p}", "-g=dba", "-o=DRYRUN", ">",
                        f"{self.stagingDir}\\missing_indices.sql"], check=True)
            logging.info("Successfully wrote missing_indices.sql")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
            raise MissingTeamcenterMethod("Missing index_verifier method, please ensure that the teamcenter bat is well defined in UpgradeChecks.bat")
    

    # CHECKERS
    # ======================================================================================================================
    
    def checkDatabaseConnectivity(self) -> None:
        
        process = subprocess.run(["cmd", "/c", "install", "-ayt"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        for line in process.stdout:
            print(line, end="")

    
    

    def checkOrganization(self, filename: str = "organization.xml", required_groups = {"Project Administration": "Project Administrator",
                                                                  "Validation Administration": "Validation Administrator", "dba": "DBA",
                                                                  "system": ""}):
        logging.info("Parsing oranisation.xml")
        tree  = ET.parse(f'{self.stagingDir}\\{filename}')
        root = tree.getroot()
        groupLeaves = root.findall("{http://www.plmxml.org/Schemas/PLMXMLSchema}Organisation")
        roleLeaves = root.findall("{http://www.plmxml.org/Schemas/PLMXMLSchema}Role")
        groups: dict[str, list] = dict()
        roleIDs = {r.attrib["id"]: r.attrib["name"] for r in roleLeaves}
        for g in groupLeaves:
            name = g.attrib["name"]
            roles = [field.attrib["dataRef"].replace("#", "") for field in g.iter() if "UserValue" in field.tag and field.attrib["title"] == 'list_of_role']
            groups[name] = roles
        
        # ReIndexing and Checking Alignment
        for k, v in groups.items():
            groups[k] = [roleIDs[rID] for rID in v]
            if k in required_groups.keys() and required_groups[k] in groups[k]:
                required_groups.pop(k)
            elif k in required_groups.keys() and required_groups[k] == "":
                required_groups.pop(k)

        if len(required_groups) != 0:
            for k, v in required_groups.items():
                logging.error(f"Missing Group: {k} | Role: {v}")
            raise MissingRoles("Please review Organization for required roles")
        
        else:
            logging.info("All required roles are present")


    def checkMissingIndices(self, filename = "missing_indices.sql") -> None :
        logging.info("Checking missing_indices.sql")
        count = 0 
        with open(f"{self.stagingDir}\\{filename}") as f:
            for line in f:
                if not (line.isspace() or line.strip().startswith("REM")):
                    logging.warning(f"You are missing the following in SQL: {line}")
                    count += 1

        

        if count:
            raise MissingIndex(f"Missing indices in SQL, please review {filename}")
        else:
            logging.info("No missing indices...")

    def checkPreferences(self, preference_filename="preferences.xml", backup_filename="backup.xml"):
        
        prefs_to_check: set = {"Default_Transient_Server", "Fms_BootStrap_Urls", "Transient_Volume_Installation_Location",
                          "Default_Transient_Volume_Id", "Transient_Volume_RootDir", "WEB_default_site_server"}
        preferences: dict[str, str] = dict()
        transientVolumes: dict[str, str] = dict()


        # PARSING PREFERENCE FILE
        logging.info("Parsing preference file")
        tree = ET.parse(f"{self.stagingDir}\\{preference_filename}")
        root = tree.getroot()
        for p in root.findall("./category/preference"):
            name = p.attrib["name"]
            if name in prefs_to_check:
                preferences[name] = [v.text for v in p.findall("./context/value")]
                prefs_to_check.remove(name)

        if len(prefs_to_check) != 0:
            for i in prefs_to_check:
                logging.warning(f"Missing {i} in preferences")
            raise MissingPreference("Please review preference configuration")
        

        # PARSING BACKUP FILE
        logging.info("Parsing backup.xml")
        backupTree = ET.parse(f"{self.stagingDir}\\{backup_filename}")
        backupRoot = backupTree.getroot()
        backupDefaultTransientVolumeID = backupRoot.find("./Default_Transient_Volume_Id").text
        backupTransientVolumes: dict[str, str] = dict()
        for tv in backupRoot.findall("./transientVolumeInfo"):
            backupTransientVolumes[tv.find("./transVolId").text] = tv.find("./wntPath").text

        errorLevel = 0
        for k, v in preferences.items():
            print()
            match(k):
                case "Default_Transient_Server":
                    logging.info("Checking Default_Transient_Server...")
                    serverName = preferences["Default_Transient_Server"][0].split(":")[1].replace('//', '')
                    if serverName.lower() == self.server.lower():
                        logging.info("Default_Transient_Server is correctly configured")
                    else:
                        logging.error(f"Default_Transient_Server reads a different servername than this one: {self.server}" \
                                                      f"\n\t\tPreferences: {serverName}\n\n ")
                        
                        errorLevel = 1
                    

                case "Fms_BootStrap_Urls":
                    logging.info("Checking Fms_BootStrap_Urls...")
                    serverName = preferences["Fms_BootStrap_Urls"][0].split(":")[1].replace('//', '')
                    if serverName.lower() == self.server.lower():
                        logging.info("Fms_BootStrap_Urls is correctly configured")
                    else:
                        logging.error(f"Fms_BootStrap_Urls reads a different servername than this one: {self.server}" \
                                        f"\n\t\tPreferences: {serverName}\n\n ")
                        errorLevel = 1
                        

                case "Transient_Volume_Installation_Location":
                    logging.info("Checking Transient_Volume_Installation_Location...")
                    serverName = preferences["Transient_Volume_Installation_Location"][0]
                    if serverName.lower() == self.server.lower():
                        logging.info("Transient_Volume_Installation_Location is correctly configured")
                    else:
                        logging.error(f"Transient_Volume_Installation_Location reads a different servername than this one: {self.server}" \
                                        f"\n\t\tPreferences: {serverName}\n\n ")
                        errorLevel = 1
                        

                case "Default_Transient_Volume_Id":
                    logging.info("Checking Default_Transient_Volume_Id...")
                    if backupDefaultTransientVolumeID not in backupTransientVolumes.keys():
                        logging.error(f"The default transient ID does not exist in the database: {backupDefaultTransientVolumeID}.\nPlease review backup.xml in {self.stagingDir}.")
                        errorLevel = 1
                    else:
                        if preferences["Default_Transient_Volume_Id"][0] == backupDefaultTransientVolumeID:
                            logging.info("The default transient volume ID is aligned between preference and database")
                        
                        else:
                            logging.error(f"The default transient ID is missaligned between preference:" \
                            f"\n\t\tBackup: {backupDefaultTransientVolumeID}\n\t\tPreferences: {preferences["Default_Transient_Volume_Id"][0]}\n\n  ")
                            errorLevel = 1


                    
                case "Transient_Volume_RootDir":
                    logging.info("Checking Transient_Volume_RootDir...")
                    if preferences["Transient_Volume_RootDir"][0] == backupTransientVolumes[backupDefaultTransientVolumeID]:
                        logging.info("Transient Volume Location is aligned")

                    else:
                        logging.error("The default transient volume location is missaligned between preference" \
                            f"\nbackup: {backupTransientVolumes[backupDefaultTransientVolumeID]}\nPreferences: {backupTransientVolumes[backupDefaultTransientVolumeID]}\n")
                        errorLevel = 1
                
                case "WEB_default_site_server":
                    logging.info("Checking WEB_default_site_server...")
                    serverName = preferences["WEB_default_site_server"][0].split(":")[0].replace('//', '')
                    if serverName.lower() == self.server.lower():
                        logging.info("WEB_default_site_server is correctly configured")
                    else:
                        logging.error(f"WEB_default_site_server reads a different servername than this one: {self.server}" \
                                                      f"\n\t\tPreferences: {serverName}\n\n  ")
                        errorLevel = 1
                case _:
                    logging.warning("Default match triggered, a preference is different in syntax. Review")
        
        print()        
        if errorLevel == 1:
            raise MissingPreference("One or more preferences is wrong. Please correct.")


        


if __name__ =="__main__":
    logging.basicConfig(level=logging.INFO,
                        format=" %(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')
    
    # upgradePreChecker = UpgradePreChecker(server_name="inchesvetc1002", staging_dir=".\\Bin\\UpgradeUtility\\")
    # upgradePreChecker.checkOrganization()
    # upgradePreChecker.checkMissingIndices()
    # upgradePreChecker.checkPreferences()