import logging
from Datashare.Item import Item
from Datashare.QueryMigration import QueryMigration
from Datashare.QueryTeamcenter import *
from Datashare.Exceptions import *
import re
from datetime import datetime
import sqlite3
import hashlib

from HelperMethods.HelperMethods import *
from HelperMethods.Errors import *
class Batch:
    def __init__(self, batch_id: str, batch_size: int, report_file_loc: str, puid_file_loc: str, item_id_file_loc: str,
                 query_teamcenter: QueryTeamcenter, query_migration: QueryMigration):
        self.BATCH_ID = batch_id
        self.BATCH_SIZE = batch_size
        self.REPORT_FILE = report_file_loc
        self.PUID_FILE = puid_file_loc
        self.ITEM_ID_FILE = item_id_file_loc

        self.queryTeamcenter: QueryTeamcenter = query_teamcenter
        self.queryMigration: QueryMigration = query_migration
        
        self.ITEMS: dict[str, Item] = dict()
        self.SKIPPED: dict[str, Item] = dict()

        self.START: datetime = datetime.now()
        self.END: datetime = None
        self.DURATION: int = None
        self.STATUS: str  = None
        self.SUCCESS_RATE: float = None


    def setStatus(self, status: str) -> None:
        self.STATUS = status


    def setEnd(self) -> None:
        """
        Mark end serves to set the self.END and self.DURATION attributes after the report file has been parsed

        ### Parameters
            - None
        
        ### Returns 
            - None
        """
        now: datetime = datetime.now()
        self.END: datetime = now
        try:
            self.DURATION: int  = int((self.END - self.START).total_seconds())
        except TypeError:
            self.DURATION = None

    def setSuccessRate(self, decimal: float):
        self.SUCCESS_RATE = decimal

    def clearMemory(self):
        self.BATCH_ID = None
        self.BATCH_SIZE = None
        self.REPORT_FILE = None
        self.PUID_FILE = None
        self.ITEM_ID_FILE = None
        self.ITEMS.clear()
        self.SKIPPED.clear()
        self.START: datetime = None
        self.END: datetime = None
        self.DURATION: int = None
        self.SUCCESS_RATE = None
    
    

    def fillBatch(self, status:str, size: int, order: str, table="MigrationItems") -> None:
        """
        Fills self.ITEMS dictionary with items with one of the following statuses after transfer:
        - SUCCESS
        - FAILED
        - NULL

        Additionally marks the objects as in progess

        :params status: Valid inputs include 'SUCCESS', 'FAILED', 'NULL'
        :params size: Size (by default None which returns all items with the declared status)
        :params order: Valid inputs: ASC or DESC
        :params table: Name of the table name by default MigrationItems

        """
        data = self.queryMigration.fetchNewBatchData(status, size, order, table, self.BATCH_ID)
        self.ITEMS = {item_id: Item(item_id, puid) for item_id, puid in data}


    def getReferenceInstanceHash(self, item_puid: str, item_revision_puid:str, dataset_puid: str, imanfile_puid: str):
        string = f"{item_puid}{item_revision_puid}{dataset_puid}{imanfile_puid}"
        return hashlib.md5(string.encode("utf-8")).hexdigest()


    def itemVolumePrecheck(self, essential_extensions= {'prt', "qaf"}) -> None:
        """
        Checks every item in a batch and determines if its files are present.
        If it is absent and marked as an important file, its volume check status will be set to false.

        It additionally updates the storge allocations of each item in a batch.

        ### Parameters
            - list of oracle configurations in the following format:
            [User, Password, Host, Port, Service Name]
            - set of essential Extensions

        ### Returns:
            - None
            
        """
        start = datetime.now()
        logging.info("Checking that all associated datasets are populated")
        # Connect to Oracle
    
        result = self.queryTeamcenter.queryItemVolumeDetails(
            [item.PUID for item in self.ITEMS.values()]
        )

        missingFiles = []
        dereferencedInstances = []


        for row in result:
            itemId, itemPuid, itemRevid, itemRevPuid, relationType, datasetType, datasetName, datasetPuid, filePuid, \
            volName, directory, filename, originalFilename = row

            pathToFile: Path = Path(directory) / filename
            try:
                if pathToFile.exists() and pathToFile.is_file():
                    fileSize = pathToFile.stat().st_size
                    self.ITEMS[itemId].addToSize(fileSize)
                
                elif pathToFile.exists():
                    logging.info(f"{pathToFile} is not a file")
                    
                else:
                    missingFiles.append((filePuid, volName, directory, filename, originalFilename))
                    instanceHash = self.getReferenceInstanceHash(itemPuid, itemRevPuid, datasetPuid, filePuid)
                    dereferencedInstances.append((instanceHash, itemId, itemPuid, itemRevid, itemRevPuid, relationType, datasetType, datasetName, datasetPuid, filePuid))

                    extention = filename.split('.')[-1]
                    
                    if extention in essential_extensions:
                        self.ITEMS[itemId].setVolumeCheckStatus(False)
                        logging.warning(f"ITEM: {itemId} with\n\t\t\tRELATION: {relationType}\n\t\t\tDATASET: {datasetType}\
                        \n\t\t\tMISSING FROM: {pathToFile}\n\n")
                        logging.info(f"{itemId} is missing {filename} as such its Volume Check Status is set to False\n")

                    else: 
                        logging.info(f"{itemId} is missing {filename}. But is not defined as a key extention its Volume Check Status is unchanged")
            
            except KeyError:
                logging.info(f"{itemId} was not found in the collection of items in the Teamcenter Database.")

        logging.info("Inserting rows to DereferencedFiles...")
        self.queryMigration.insertDerefencedFiles(dereferencedInstances)

        logging.info("Inserting rows to MissingImanfiles...")
        self.queryMigration.insertMissingFiles(missingFiles)
        logging.info(f"Items validated in volumes successfully in {round((datetime.now() - start).total_seconds(), 2)} seconds.")


    def separateSkipped(self) -> None:
        """
        Separate Skipped updates the batches self.ITEMS and self.SKIPPED dictionaries to post queryVolumeInfo.
        For the purpose of only sending items not missing essential_extensions (.prt) if the Check Volumes is
        enabled.

        ### Parameters
            - None
        
        ### Returns
            - None
        """

        for item_id, item in self.ITEMS.items():
            if not item.PASSED_VOLUME_CHECK:
                item.setStatus("MISSING DATASET REFERENCE")
                self.SKIPPED[item_id] = item


        for item_id in list(self.SKIPPED.keys()):
            logging.info(F"Removing {item_id} from batch")
            del self.ITEMS[item_id] 


    def analyseReport(self, latest_ds_version: bool, success_rate_threshold=0.25) -> None:
        """
        Reads the report file generated by data_share -report and outputs a list of
        tuples in the form (ID, Type, Status, Error, Comment, Transaction ID)
    
        Input:
            - Report File Name
        Output:
            - Error Level: Int (0: None, 1: Push to Redo, 2: Critical, end datashare script)
    
        """
        statuses_to_print = []
        N = 0
        nFails = 0
    
        with open(self.REPORT_FILE) as file:
            for line in file:
                if line.startswith("\n") or line.startswith("Object Id/Name") or line.startswith("*") or line.startswith("(")\
                    or line.startswith("Parent Process") or line.startswith("Process") or line.startswith("REST"):
                    continue
            
                split = re.split(r"\s{3,}", line)       # CHANGE TO REPORT FORMAT
                n = len(split) 
                if n >= 4 and n <= 6:
                    try:                      
                        object_id = split[0]
                        object_type = split[1]
                        status = split[2]
                        error = 0
                        comment = ''

                        if "FAILED" in status:
                            error = int(split[3])
                            comment = split[4]
                            nFails += 1
                        
                        transaction_id = int(split[-1].strip())

                    except ValueError:
                        transaction_id = 0
                    
                    try:
                        if "SUCCESS" in status and latest_ds_version:
                            status += " - WITH LATEST DATASET"
                            
                        self.ITEMS[object_id].setTransactionAttributes(object_type, status, error, comment, transaction_id)
                        statuses_to_print += [f"\tobject_id = {object_id}", f"status = {status}"]
                    
                    # To not crash script during inconsistent keys between Report file and database. These items will be marked FAILED WITH INCONSISTENT NAMES
                    except KeyError:
                        statuses_to_print += [f"\tobject_id = {object_id} was not found in the database", f"Marking status as NOT FOUND IN REPORT"]
                                                    
                    N += 1

        # MAY THROW FILE NOT FOUND -> CAUGHT IN MERCURY
        
        if len(statuses_to_print) != 0:
            success_rate = round((1 - nFails / N), 3)
            logging.info("Report file read correctly\n")
            self.setSuccessRate(success_rate)
            
            if success_rate >= success_rate_threshold:
                print(displayTabulatedItems(statuses_to_print, 45, 2))
                logging.info(f"The batch passed the minimum success threshold with a success rate of {success_rate* 100}%")
                statuses_to_print.clear()
                return

            else:
                logging.warning(f"The success rate of the batch was {success_rate* 100}% which is lower than the threshold of {success_rate_threshold* 100}%")
                raise FailedSuccessThreshold(f"The success threshold did not meet the mininum of {success_rate_threshold}")
                
            
        else:
            logging.error("Empty report file. No statuses were updated. Please check the IDSM connection between target and source sites")
            raise EmptyReport("There was an empty report file. data_share did not conclude correctly")


    def skimReportForRate(self):
        """
        Reads report file to set the total success rate
        """

        N = 0
        nFails = 0
        
        with open(self.REPORT_FILE) as file:
            for line in file:
                if line.startswith("\n") or line.startswith("Object Id/Name") or line.startswith("*") or line.startswith("(")\
                    or line.startswith("Parent Process") or line.startswith("Process") or line.startswith("REST"):
                    continue
                else:
                    split = re.split(r"\s{3,}", line)
                    n = len(split) 
                    if n >= 4 and n <= 6:                      
                            
                        status = split[2]
                        if "FAILED" in status:
                            nFails += 1
                        
                    N += 1

        try:
            successRate = float(1 - nFails / N)
            self.setSuccessRate(successRate)
            logging.info(f"The batches had a success rate of {successRate * 100}%")

        except ZeroDivisionError:
            raise EmptyReport("The report was found to be empty.")