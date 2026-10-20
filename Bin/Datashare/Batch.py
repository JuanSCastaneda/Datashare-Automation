import logging
from Datashare.Item import Item
import re
import oracledb
from datetime import datetime
import sqlite3

from HelperMethods.HelperMethods import *
from HelperMethods.Errors import *

class Batch:
    def __init__(self, batch_id: str, batch_size: int, report_file_loc: str, puid_file_loc: str, item_id_file_loc: str):
        self.BATCH_ID = batch_id
        self.BATCH_SIZE = batch_size
        self.REPORT_FILE = report_file_loc
        self.PUID_FILE = puid_file_loc
        self.ITEM_ID_FILE = item_id_file_loc
        
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
    
    

    def fillBatch(self, status:str, size: int, order: str, database= "migration.db", table="MigrationItems") -> None:
        """
        Fills self.ITEMS dictionary with items with one of the following statuses after transfer:
        - SUCCESS
        - FAILED
        - NULL

        ### Parameters
        - Status (valid inputs include 'SUCCESS', 'FAILED', 'NULL')
        - Batch Size (by default None which returns all items with the declared status)
        - Order (valid inputs: ASC or DESC)
        - Database Connection (name of SQLite Database)
        - Table (Name of the table name by default MigrationItems)
        
        ### Returns
        None

        """
        command = ""
        try:
            conn = sqlite3.connect(database)
            cursor = conn.cursor()

            if status == "NULL":
                command = f"SELECT item_id, puid FROM {table} WHERE import_status is NULL"

            elif status == "SUCCESS" or status == "FAILED":
                command = f"SELECT item_id, puid FROM {table} WHERE import_status LIKE '{status}%'"
            
            else:
                raise InvalidInput("ERROR 2901: Invalid status input. Please use FAILED, SUCCESS, or NULL.")

            match order.upper():
                case "ASC":
                    command += " ORDER BY ROWID ASC"
                case "DESC":
                    command += " ORDER BY ROWID DESC"
                case _:
                    pass

            
            if size != 0:
                command += f" LIMIT {size}"
                
            cursor.execute(command)

            items = cursor.fetchall()

            logging.debug("Marking all items as 'IN PROGRESS'")
            cursor.executemany(f'''
                                    UPDATE {table}
                                    SET import_status = ?, batch_id = ?
                                    WHERE puid = ?
                                ''', [("IN PROGRESS", self.BATCH_ID, i[1])    # puid
                                        for i in items])     
            
            
            self.ITEMS = {item_id: Item(item_id, puid) for item_id, puid in items}

        finally:
            conn.commit()
            conn.close()


    def queryOracleVolumeInfo(self, oracle_configs: list, sitename: str, essential_extensions= {'prt', "qaf"}) -> None:
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
        usr, pwd, host, port, serviceName = oracle_configs
        # Connect to Oracle
        
        connection = oracledb.connect(
            user=f'{usr}',
            password=f'{pwd}',
            dsn=f'{host}:{port}/{serviceName}')
    
        cursor = connection.cursor()
        placeholder = ", ".join([f":{i+1}" for i in range(len(self.ITEMS))])
    
        query = f"""
            SELECT item.puid, item.pitem_id, relationtype.ptype_name, datasettype.pdatasettype_name,
                volumes.PWNT_PATH_NAME, imanfile.PSD_PATH_NAME, imanfile.PFILE_NAME
            
                FROM PITEM item
                JOIN PITEMREVISION itemrevision
                    ON item.puid = itemrevision.RITEMS_TAGU
                JOIN PIMANRELATION relation
                    ON itemrevision.puid = relation.RPRIMARY_OBJECTU
                JOIN PIMANTYPE relationtype
                    ON relationtype.puid = relation.RRELATION_TYPEU
                JOIN PDATASET dataset
                    ON dataset.puid = relation.RSECONDARY_OBJECTU
                JOIN {"PREF_LIST_0" if sitename.lower().strip() != "shlab10" else "PREF_LIST"} reflist
                    ON dataset.puid = reflist.puid
                JOIN PDATASETTYPE datasettype
                    ON datasettype.puid = dataset.RDATASET_TYPEU
                JOIN PIMANFILE imanfile
                    ON reflist.pvalu_0 = imanfile.puid
                JOIN PIMANVOLUME volumes
                    ON imanfile.RVOLUME_TAGU = volumes.puid
            WHERE item.puid IN ({placeholder})"""
    
        result = cursor.execute(query, [item.PUID for item in self.ITEMS.values()]).fetchall()
        connection.close()

        for row in result:
            _, item_id, relation, datasettype, path, subdir, filename = row
            pathToFile: Path = Path(path) / subdir / filename
            try:
                if pathToFile.exists() and pathToFile.is_file():
                    fileSize = pathToFile.stat().st_size
                    self.ITEMS[item_id].addToSize(fileSize)
                
                elif pathToFile.exists():
                    logging.info(f"{pathToFile} is not a file")
                    
                else:
                    extention = filename.split('.')[-1]
                    
                    if extention in essential_extensions:
                        self.ITEMS[item_id].setVolumeCheckStatus(False)
                        logging.warning(f"ITEM: {item_id} with\n\t\t\tRELATION: {relation}\n\t\t\tDATASET: {datasettype}\
                        \n\t\t\tMISSING FROM: {path+ '\\' + subdir + '\\'+ filename}\n\n")
                        logging.info(f"{item_id} is missing {filename} as such its Volume Check Status is set to False\n")

                    else: 
                        logging.info(f"{item_id} is missing {filename}. But is not defined as a key extention its Volume Check Status is unchanged")
            
            except KeyError:
                logging.info(f"{item_id} was not found in the collection of items in the Teamcenter Database.")

        logging.info(f"Items validated in volumes successfully in {round((datetime.now() - start).total_seconds(), 2)} seconds.")


    # def queryMSSQLVolumeInfo()            To be added when MSSQL functionality is required

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


    def analyseReport(self, latest_ds_version: bool, success_rate_threshold=0.25, ) -> int:
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
        
        try:
            with open(self.REPORT_FILE) as file:
                for line in file:
                    if line.startswith("\n") or line.startswith("Object Id/Name") or line.startswith("*") or line.startswith("(")\
                        or line.startswith("Parent Process") or line.startswith("Process") or line.startswith("REST"):
                        continue
                    else:
                        split = re.split(r"\s{3,}", line)
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
                        
        except FileNotFoundError as fnf:
            logging.error(f"2701: {fnf.filename} was not found. Resubmiting datashare")
            return 2701
        
        if len(statuses_to_print) != 0:
            success_rate = round((1 - nFails / N), 3)
            logging.info("Report file read correctly\n")
            self.setSuccessRate(success_rate)
            
            if success_rate >= success_rate_threshold:
                print(displayTabulatedItems(statuses_to_print, 45, 2))
                logging.info(f"The batch passed the minimum success threshold with a success rate of {success_rate* 100}%")
                statuses_to_print.clear()
                return 2001

            else:
                logging.warning(f"2501: The success rate of the batch was {success_rate* 100}% which is lower than the threshold of {success_rate_threshold* 100}%")
                return 2501
                
            
        else:
            logging.error("2902: No statuses were updated. Please check the IDSM connection between target and source sites")
            return 2902


    def skimReportForRate(self):
        """
        Reads report file to set the total success rate
        """

        N = 0
        nFails = 0
        
        try:
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

            successRate = float(1 - nFails / N)
            self.setSuccessRate(successRate)
            logging.info(f"The batches had a success rate of {successRate * 100}%")

                        
        except FileNotFoundError as fnf:
            logging.warning(f"Could not find report file...")
            pass