from subprocess import run, Popen, PIPE
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import logging
import re
from datetime import datetime
from time import sleep

class VolumeCreator:
    def __init__(self, transaction_file: str = "Created.log", fscID: str ="FSC_LUDUDSVPTCC01_husky1sapateamcenter", u:str = "infodba", p="infPW4imn$", creation_threshold=.2):
        self.transactionFile = transaction_file
        self.volumeName = None
        self.nodeName = None
        self.volumePath = None
        self.fscID = fscID
        self.u = u
        self.p = p
        self.creationThreshold = creation_threshold


        self.setDefaultVolume(self.checkCurrentDefaultVolume())

    def __str__(self):
        return f"\n\tVOL: {self.volumeName}\n\tNODE: {self.nodeName}\n\tPATH: {self.volumePath}"


    def checkCurrentDefaultVolume(self) -> None:
        command = ['cmd.exe', '/c', 'ExportCurrentVolume.bat', self.u, self.p]
        logging.info("Exporting Current Default Volume Config")
        process = run(command, text=True, capture_output=True)

        if process.returncode != 0:
            logging.error("An issue occurred exporting current configuration")
            raise RuntimeError



        tree = ET.parse(".\\volume.xml")
        root = tree.getroot()
        vault = root.find("{http://www.plmxml.org/Schemas/PLMXMLSchema}Vault")
        
        volumeAttributes = dict()
        volumeAttributes["name"] = vault.attrib["name"]
        
        for child in vault.iter():
            if "UserValue" in child.tag:
                volumeAttributes[child.attrib["title"]] = child.attrib["value"]


        self.deleteVolumeFile()

        return volumeAttributes
    
    def checkCurrentVolumeAlignment(self) -> bool:
        
        attributes = self.checkCurrentDefaultVolume()
        alignment = True if self.volumeName == attributes["name"] and \
        self.nodeName == attributes["node_name"] and \
        self.volumePath == attributes["wnt_path_name"] else False

        
        if alignment:
            logging.info("Current volume configuration is aligned with this one")
        
        else:
            logging.warning(f"Current volume configuration is misaligned with this one: {self}")
            logging.info(f"Updated config to: {self}")
            self.setDefaultVolume(attributes)


        return alignment       
        


    def setDefaultVolume(self, attributes):
        self.volumeName = attributes["name"]
        self.nodeName = attributes["node_name"]
        self.volumePath = attributes["wnt_path_name"]

        logging.info(f"Volume Name: {self.volumeName}")
        logging.info(f"Volume Path: {self.volumePath}")
        logging.info(f"Volume Node: {self.nodeName}")

    
    def checkFileCount(self) -> int:        
        subdir = None

        for sd in os.listdir(self.volumePath):
            if os.path.isdir(self.volumePath + '\\' + sd) and "dba" in sd:
                subdir = sd
        
        if not subdir is None:
            logging.info(rf"Finding file count in {self.volumePath + "\\" + subdir}")
            command = ['cmd.exe', '/c', rf'dir /a-d /b /s {self.volumePath + '\\' + sd}']
            process1 = Popen(command, text=True, stdout=PIPE)
            process2 = Popen(["find", "/c", "/v", ""], stdin=process1.stdout, stdout=PIPE, text=True)
            process1.stdout.close()
            output, _ = process2.communicate()

            
        else:
            logging.error("Could not locate dba subdirectory")
            raise RuntimeError

        
        n = int(output.strip())
        logging.info(f"{self.volumeName} contains: {n:,} files")

        return n
    


    def increaseCounter(self) -> None:
        pattern = re.compile(r"(?P<prefix>[A-Za-z]+)(?P<count>\d+)")
        
        logging.info(f"Current Volume Name: {self.volumeName}")
        logging.info(f"Current Volume Path: {self.volumePath}\n\n")             
        if match := pattern.fullmatch(self.volumeName):
            gd = match.groupdict()
            prefix = gd["prefix"]
            count = int(gd["count"])

        
        self.volumeName = f"{prefix}{(count + 1):03d}"
        self.volumePath = f"{"\\".join(self.volumePath.split("\\")[:-1])}\\{self.volumeName}"
        logging.info(f"New Volume Name: {self.volumeName}")
        logging.info(f"New Volume Path: {self.volumePath}\n\n") 


    def implementNewVolume(self):
        logging.info("Implementing a new volume")
        logging.info("Executing...")
        command = ["cmd.exe", "/c", "MakeVolume.bat", self.u, self.p, self.volumeName, self.volumePath, self.nodeName, self.fscID]
        
        process = run(command, text=True, capture_output=True)


        if process.returncode == 0:
            with open(self.transactionFile, "a") as file:
                file.write(f"\n{datetime.now()} Created New Volume: {self.volumeName}")
                file.write(f"\n{datetime.now()} Assigned {self.volumeName} to dba\n\n")
            
        else:
            with open(self.transactionFile, "a") as file:
                file.write(f"\n{datetime.now()} Failed to create or assign new volume to dba")
            
            raise RuntimeError

    def loop(self, timeout: int = 120):

        while True:
            
            if self.checkCurrentVolumeAlignment():

                logging.info(f"Checking current volume size")
                n = self.checkFileCount()
                
                fullness = n / 4e6
                if fullness > self.creationThreshold:
                    logging.info(f"The current volume is at {round(fullness*100, 1)}% occupancy. Which is higher than the threshold of {round(self.creationThreshold*100, 1)}%. Creating new volume")
                    self.increaseCounter()
                    self.implementNewVolume()

                else:
                    logging.info(f"The current volume is at {round(fullness*100, 1)}% occupancy. Which is lower than the threshold of {round(self.creationThreshold*100, 1)}%. ")
                
                
                logging.info(f"Sleeping for the next {timeout} minutes")
            
            sleep(timeout*60)

            
    def deleteVolumeFile(self):
        os.remove(r".\volume.xml") 
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')
    vc = VolumeCreator()
    vc.loop()
