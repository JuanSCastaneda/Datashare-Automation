"""
Mercury serves as the central object to iterate through the database and send packages (batches)
of Items to Teamcenter's data_share utility. It's responsibility is to catch errors, record results,
and send objects between source and target sites.

"""

import sqlite3
import re
import subprocess 
import time
from Datashare.Batch import Batch
from Datashare.Item import Item
from HelperMethods.HelperMethods import *
import gc
from datetime import datetime
import logging
import json

class Mercury:
    def __init__(self, batch_size:int = 100, oaat: bool = True, skip_missing_datasets: bool = True, source_table:str = "MigrationItems", mode="FULL", status="NULL",
                 order= "ASC", success_threshold=0.25, configurationFile= r"Configuration\configuration.json", adapting_oaat: bool = False, log:bool = False, latest_ds = False,
                 transfer_option_set = "HuskyMultiSiteExpOptSet"):
        with open(configurationFile, "r") as file:
            data = json.load(file)

        # DATABASE MANAGEMENT SYSTEM VARIABLES
        self.DBMgtSystem = 'Oracle' if data['Oracle'] == True else 'MSSQL'

        match self.DBMgtSystem:
            case 'Oracle':
                self.ORACLE_USER = data['OracleUser']
                self.ORACLE_PASSOWRD = data['OraclePassword']
                self.ORACLE_HOST = data['OracleHost']
                self.ORACLE_PORT = data['OraclePort']
                self.ORACLE_SERVICE = data['OracleService']

            case 'MSSQL':
                self.ORACLE_USER = ''
                self.ORACLE_PASSOWRD = ''
                self.ORACLE_HOST = ''
                self.ORACLE_PORT = ''
                self.ORACLE_SERVICE = ''

        # DATASHARE CONFIGURATIONS
        self.SOURCE: str = data['SourceSiteName']
        self.TARGET: str = data['TargetSiteName']
        self.DB: str = data['SQLiteDatabaseName']
        self.BATCH_SIZE: int = batch_size
        self.OAAT: bool = oaat
        self.ADAPTING_OAAT: bool = adapting_oaat
        self.SKIP_MISSING: bool = skip_missing_datasets
        self.SOURCE_TABLE: str = source_table
        self.QUERY_STATUS: str = status.upper()
        self.MODE: str = mode.upper()
        self.ORDER: str = order.upper()
        self.SUCCESS_THRESHOLD: float = success_threshold
        self.LOG = log
        self.LATEST_DS = latest_ds  
        self.TRANSFER_OPTION_SET = transfer_option_set
        self.TARGET_IDSM = None

        # DYNAMIC VARS
        self.BATCH: Batch = None
        self.COUNT: int = 1
        self.REDO: bool = False
        self.RETRIED_LOOP: bool = False

    def setBatchSize(self, batch_size: int):
        self.BATCH_SIZE = batch_size

    def setOaat(self, oaat:bool):
        self.OAAT = oaat

    def setSkipMissingDatasets(self, skip_missing_datasets: bool):
        self.SKIP_MISSING = skip_missing_datasets
    
    def setSourceTable(self, source_table: str):
        self.SOURCE_TABLE = source_table

    def setQueryStatus(self, status: str):
        self.QUERY_STATUS = status

    def setMode(self, mode:str): 
        self.MODE = mode

    def setOrder(self, order: str):
        self.ORDER = order if order.upper() == "ASC" or order.upper() == "DESC" else "ASC"

    def setSuccessThreshold(self, success_threshold: float):
        self.SUCCESS_THRESHOLD = success_threshold

    def setTargetIDSM(self, target_idsm):
        self.TARGET_IDSM = target_idsm

    def setLatestDS(self, latest_ds):
        self.LATEST_DS = latest_ds

    def setTransferOptionSet(self, option_set: str):
        self.TRANSFER_OPTION_SET = option_set

    def setBatch(self, batch: Batch):
        self.BATCH = batch

    def setRedo(self, boolean: bool):
        self.REDO = boolean

    def setRetriedloop(self, boolean: bool):
        self.RETRIED_LOOP = boolean

    def setLog(self, boolean: bool):
        self.LOG = boolean

    def cleanMemory(self) -> None:
        """
        Empties all fields in the Batch Item and calls the garbage collector explicitly

        ### Parameters
            - None
        ### Returns
            - None
        """
        self.BATCH.clearMemory()
        gc.collect()


    def connect(self) -> tuple:
        """
        A wrapper class for connecting to the database with extra verboseness
        
        ### Parameters
            - None
        ### Returns
            - Instance of sqlite3.connection
            - Instance of sqlite3.connection.cursor
            
        """
        logging.info(f"Connecting to {self.DB}")
        N = 5
        for i in range(N):
            
            try:
                connection = sqlite3.connect(self.DB, timeout=5)
                cursor = connection.cursor()

                break
            
            except sqlite3.OperationalError as ope:
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i}/{N}]")
                time.sleep(5)
                connection = None
                cursor = None
        
            except Exception as e:
                connection = None
                cursor = None
                logging.info(f"Failed to connect with the following SQLite3 error: {e}")

        return connection, cursor

    
    def datashareOAAT(self):
        """
        Datashare performs the operation of sending the written files to Teamcenter's data_share utility,
        records the time stamp items were sent, and calculates their duration. 
    
        ### Parameters
            - None
        ### Returns
            - None
        """
        datashareCmd = [
                'data_share',
                '-u=infodba',
                '-p=infodba',
                '-g=dba',
                '-f=send',
                f'-site={self.TARGET}',
                '-include_pfmembers',
                rf'-report={self.BATCH.REPORT_FILE}',
                "-classoffile=Tagstring",
                f'-optionset={self.TRANSFER_OPT_SET}',
                "-continue_on_error",
                rf'-filename={self.BATCH.PUID_FILE}',
                '-oaat']
        
        if self.LATEST_DS:
            datashareCmd += ["-latest_ds_version"]

        if self.LOG:
            datashareCmd += ["-log"]

        
        logging.info(f"Executing...")
        print("\n\n\tdata_share")
        for arg in datashareCmd[1:]:
            print(f"\t\t{arg}")

        print("\n\n")
        process = subprocess.Popen(datashareCmd,
                                text=True,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE
                                )
        

        # RECORDS TIME PER ITEM
        pattern = re.compile(r"Sending (?P<index>\d+) of (?P<total>\d+): (?P<item_id>\w+)([-]*)(?P<object_name>.*) to following sites...")

        item_list = list(self.BATCH.ITEMS.keys())
        successfulRead = False
        width = 90

        for line in process.stdout:
            match = pattern.match(line)

            if match:
                gd = match.groupdict()
                string = f"Sending {gd['item_id']}: ({gd['object_name']})" if gd['object_name'] != '' else f"Sending {gd['item_id']}"
                index = f"({gd['index']}/{gd['total']})"
                logging.info(f"{string} {(width - len(string) - len(index)) * '.'} {index}")
                now = datetime.now()
                i = int(gd['index']) - 1     # To be consistent with Python's indexing

                if i > 0:
                    self.BATCH.ITEMS[item_list[i]].setStart()
                    self.BATCH.ITEMS[item_list[i - 1]].setEnd()
                
                else:
                    self.BATCH.ITEMS[item_list[i]].setStart()
                    successfulRead = True

        # To capture the end time of the last item
        if successfulRead:
            self.BATCH.ITEMS[item_list[i]].setEnd()

        logging.info("Sleeping for 3 seconds to allow the report file to generate...\n")
        time.sleep(3)

        out, err = process.communicate()

        if err:
            logging.info(f"ERROR: {err} {out.decode("utf-8")}")
            

    def datashare(self):
        """
        Datashare performs the operation of sending the written files to Teamcenter's data_share utility,
        records the time stamp items were sent, and calculates their duration. 
    
        ### Parameters
            - None
        ### Returns
            - None
        """
        datashareCmd = [
                'data_share',
                '-u=infodba',
                '-p=infodba',
                '-g=dba',
                '-f=send',
                f'-site={self.TARGET}',
                '-include_pfmembers',
                rf'-report={self.BATCH.REPORT_FILE}',
                "-classoffile=Tagstring",
                f'-optionset={self.TRANSFER_OPT_SET}',
                "-continue_on_error",
                rf'-filename={self.BATCH.PUID_FILE}']

        if self.LATEST_DS:
                    datashareCmd += ["-latest_ds_version"]

        if self.LOG:
            datashareCmd += ["-log"]

        
        logging.info(f"Executing...")
        print("\n\n\tdata_share")
        for arg in datashareCmd[1:]:
            print(f"\t\t{arg}")

        print("\n\n")
        process = subprocess.Popen(datashareCmd,
                                text=True,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE
                                )
        for line in process.stdout:
            if not line.isspace():
                logging.info(line.replace('\n', ''))
        
        logging.info("Sleeping for 5 seconds to allow the report file to generate...\n")
        time.sleep(5)

        out, err = process.communicate()

        if err:
            logging.info(f"ERROR: {err} {out.decode("utf-8")}")


    def getTime(self, string: str) -> datetime:
        """
        GetTime reads a string in the form YYYY-MM-DD=HH-MM-SS and returns a datetime instance.
        
        :param: string: in the form 'YYYY-MM-DD=HH-MM-SS'

        :returns: Datetime Object

        """
        year, month, day, hour, minute, second = re.split("[=-]", string)
        arguments = [int(i) for i in [year, month, day, hour, minute, second]]
        return datetime(*arguments)

    
    def getLastNSuccessRates(self, N: int) -> list[float]:

        connection, cursor = self.connect()
        data = [i[0] for i in cursor.execute(f"SELECT success_rate FROM MigrationBatchs ORDER BY ROWID DESC LIMIT {N}").fetchall()]
        connection.close()

        return data
    

    def formatTime(self, instant: datetime) -> str:
        """
        Returns a string in the form YYYY-MM-DD=HH-MM-SS with the current time
        
        :param: None

        :returns: String

        """
        return instant.strftime("%Y-%m-%d=%H-%M-%S")
        
    

    def updateBatchTable(self, cursor) -> None:
        """
        ## Update Batch Table
        Inserts the following row in the MigrationBatchs table:

        [Batch ID | Start Time | End Time | Status | List of Items File | Repor File | Size | Duration]

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """
        
        batch: Batch = self.BATCH
        start: str = self.formatTime(batch.START)
        end: str = self.formatTime(batch.END)
        
        logging.info(f"Batch Status: {batch.STATUS}")
        logging.info("Updating MigrationBatchs Table... ")


        N = 5
        for i in range(1, N + 1):
            
            try:
                cursor.execute('''
                INSERT INTO MigrationBatchs
                (batch_id, run_start_date, run_end_date, run_status, list_of_ids_filename, report_filename, batch_size, duration, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (batch.BATCH_ID, start, end, batch.STATUS, batch.ITEM_ID_FILE, batch.REPORT_FILE, batch.BATCH_SIZE, batch.DURATION, batch.SUCCESS_RATE))
                                
                break
            
            except sqlite3.OperationalError as ope:
                if i == 5:
                    raise RuntimeError("The database was still locked after 5 tries")
                
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i + 1}/{N}]")
                time.sleep(5)

        
    def updateWSOasSent(self, cursor) -> None :
        """
        ## Update Items Table
        Updates rows in the MigrationWSO table to add:

        [ Import Status | Batch ID | Datashare Date | Size | Duration]

        Where item.PUID is in self.BATCH.ITEMS.values()

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """
        
        logging.info(f"Updating {len(self.BATCH.ITEMS)} Processed Items in The {self.SOURCE_TABLE} Table...")
        
        N = 5
        for i in range(1, N + 1):
            try:
                cursor.executemany(f'''
                        UPDATE {self.SOURCE_TABLE}
                        SET import_status = ?, batch_id = ?, data_share_date = ?, transfer_time = ? 
                        WHERE puid = ?
                    ''', [("SENT", self.BATCH.BATCH_ID , self.BATCH.END, item.DURATION, item.PUID)
                            for item in self.BATCH.ITEMS.values()])     
                break
            
            except sqlite3.OperationalError as ope:
                if i == 5:
                    raise RuntimeError("The database was still locked after 5 tries")
                
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i + 1}/{N}]")
                time.sleep(5)



    def updateItemsTable(self, cursor) -> None:
        """
        ## Update Items Table
        Updates rows in the MigrationBatchs table to add:

        [ Import Status | Batch ID | Datashare Date | Size | Duration]

        Where item.PUID is in self.BATCH.ITEMS.values()

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """
        
        logging.info(f"Updating {len(self.BATCH.ITEMS)} Processed Items in The {self.SOURCE_TABLE} Table...")

        
        N = 5
        for i in range(1, N + 1):
            
            try:
                cursor.executemany(f'''
                        UPDATE {self.SOURCE_TABLE}
                        SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                        WHERE puid = ?
                    ''', [(item.STATUS, self.BATCH.BATCH_ID , self.BATCH.END, item.SIZE, item.DURATION, item.PUID)
                          for item in self.BATCH.ITEMS.values()])
        
                if self.SKIP_MISSING:
                    n = len(self.BATCH.SKIPPED)
                    if n > 0:
                        logging.info(f"Updating {n} Skipped Items in {self.SOURCE_TABLE} Table to have [import_status: MISSING DATASET REFERENCE]...")
                        cursor.executemany(f'''
                                    UPDATE {self.SOURCE_TABLE}
                                    SET import_status = ?, batch_id = ?, data_share_date = ? WHERE puid = ?''',
                                    [(item.STATUS, self.BATCH.BATCH_ID , self.BATCH.END, item.PUID)
                                    for item in self.BATCH.SKIPPED.values()])

                    else:
                        logging.info("This batch had no items missing essential datasets")           
                
                break
            
            except sqlite3.OperationalError as ope:
                if i == 5:
                    raise RuntimeError("The database was still locked after 5 tries")
                
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i + 1}/{N}]")
                time.sleep(5)
        
        
    def updateFailedItemsTable(self, cursor) -> None:
        """
        ## Update Failed Items Table
        Inserts the following row in the FailedItems table:

        [ Item ID | Object Type | Batch ID | Import Status | Error | Comment | Date | Puid ]

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """
        failedItems = [(item.ITEM_ID, item.TYPE, self.BATCH.BATCH_ID, item.STATUS, item.ERROR, item.COMMENT, self.formatTime(self.BATCH.END), item.PUID) \
                        for item in self.BATCH.ITEMS.values() if "FAILED" in item.STATUS]
        n = len(failedItems)

        N = 5
        for i in range(1, N + 1):
            
            try:
                if n > 0:
                    logging.info(f"Appending {n} Items to The FailedItems Table...")
                    cursor.executemany("""INSERT INTO FailedItems (item_id, object_type, batch_id, import_status, error, comment, data_share_date, puid)
                            VALUES (?,?,?,?,?,?,?,?)""", failedItems)

                    logging.info(f"There was {n} failed item(s).")
                
                else:
                    logging.info("This batch contained no failed items.")
                
                break
            
            except sqlite3.OperationalError as ope:
                if i == 5:
                    raise RuntimeError("The database was still locked after 5 tries")
                
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i + 1}/{N}]")
                time.sleep(5)
        
        

    def failureRecoveryUpdate(self, cursor) -> None:
        """
        ## Updates Database
        ### Updates rows in the FailedItems table to change / delete:
        [ Batch ID | Import Status | Error | Comment | Date ]
        ### Updates

        Where item.PUID is in self.BATCH.ITEMS.values()

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """

        corruptedItems: list[Item] = []
        recoveredItems: list[Item] = []
        for i in self.BATCH.ITEMS.values():
            if "FAILED" in i.STATUS:
                corruptedItems.append(i)
            elif "SUCCESS" in i.STATUS:
                recoveredItems.append(i)

        N = 5
        for i in range(1, N + 1):
            
            try:
                logging.info(f"Updating {len(corruptedItems)} Corrupt Items in The FailedItems Table...")
                cursor.executemany('''
                                UPDATE FailedItems
                                SET batch_id = ?, import_status = ?, error = ?, comment = ?, data_share_date = ? 
                                WHERE puid = ?
                            ''', [(self.BATCH.BATCH_ID, "CORRUPT", item.ERROR, item.COMMENT, self.formatTime(self.BATCH.END), item.PUID)
                                for item in corruptedItems])
                
                
                logging.info(f"Deleting {len(recoveredItems)} Recovered Items in The FailedItems Table...")
                cursor.executemany("DELETE FROM FailedItems WHERE puid = ?", [(item.PUID,) for item in recoveredItems])

                logging.info(f"Updating {len(recoveredItems)} Recovered Items in The {self.SOURCE_TABLE} Table...")
                cursor.executemany(f"""UPDATE {self.SOURCE_TABLE}
                                    SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                                    WHERE puid = ?""",
                                    [(item.STATUS, self.BATCH.BATCH_ID , self.BATCH.END, item.SIZE, item.DURATION, item.PUID)
                                        for item in recoveredItems])
                
                logging.info(f"Updating {len(corruptedItems)} Corrupt Items in The {self.SOURCE_TABLE} Table...")
                cursor.executemany(f"""UPDATE {self.SOURCE_TABLE}
                                    SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                                    WHERE puid = ?""",
                                    [("CORRUPT", self.BATCH.BATCH_ID , self.BATCH.END, item.SIZE, item.DURATION, item.PUID)
                                        for item in corruptedItems])
                
                break
                    
            except sqlite3.OperationalError as ope:
                if i == 5:
                    raise RuntimeError("The database was still locked after 5 tries")
                
                logging.warning(f"The database is currently locked due to another processes writing in it. Retrying to connect in 5s [Attempt: {i + 1}/{N}]")
                time.sleep(5)
        



    #%% MAIN DATASHARE FUNCTION
    def datashareLoop(self) -> int:
        """
        Datashare enters a loop of sending objects to the data_share utility by leveraging subprocess.Popen(...)

        ### Parameters
            - None

        ### Returns
            - None
        """
        # PRINTING TITLE
        # ---------------------------------------------------------------------------------------------------
        width = 110
        title = "DATASHARE AUTOMATION"
        print(f"\n\n{'='*width}\n{' '* int((width -len(title))/2)}{title}\n{width*'='}\n\n")

        print("Using:")
        print(f"\tBatchSize: {self.BATCH_SIZE}")
        print(f"\tOAAT: {self.OAAT}")
        print(f"\tSkip Missing Datasets: {self.SKIP_MISSING}")
        print(f"\tQuery Status: {self.QUERY_STATUS}")
        print(f"\tMODE: {self.MODE}")
        print(f"\tOrder: {self.ORDER}")
        print(f"\tSource Table: {self.SOURCE_TABLE}")
        print(f"\tRouting IDSM: {self.TARGET_IDSM}")
        print(f"\tMinimum Success Threshold: {round(self.SUCCESS_THRESHOLD*100)} %")
        print(f"\tTransfer Option Set: {self.TRANSFER_OPTION_SET}")


        # INITIALIZATION
        # ---------------------------------------------------------------------------------------------------
        
        while True:
            
            # PRINTING HEADER
            # ---------------------------------------------------------------------------------------------------
            header = f"BATCH {self.COUNT} - RUN ONE ITEM AT A TIME" if self.REDO or self.OAAT else f"BATCH {self.COUNT} DETAILS"
            print(f"\n{'-'*width}\n{' '*int((width - len(header)) /2)}{header}\n{'-'*width}\n")
            

            # BATCH INITIALIZATION
            # ---------------------------------------------------------------------------------------------------
            
            start: datetime = datetime.now()
            startTimeStr = self.formatTime(start)    # Format: YYYY-MM-DD=HH-MM-SS
            
            if True: # testing this block always true not self.REDO or self.RETRIED_LOOP:
                suffix = "_FR" if self.QUERY_STATUS == "FAILED" else ""
                batch_id = f'{self.SOURCE}_{startTimeStr}_{self.BATCH_SIZE}_{self.TARGET_IDSM}_{self.ORDER}{suffix}'
                puid_file = rf'Items\PUID\PUID_{batch_id}.txt'
                item_id_file = rf'Items\ItemID\item_list_{batch_id}.txt'
                report_file = rf'Reports\report_{batch_id}.txt'
                self.setBatch(Batch(batch_id, self.BATCH_SIZE, report_file, puid_file, item_id_file))
                

            
            # DISPLAY BATCH INFORMATION
            # ---------------------------------------------------------------------------------------------------
            w = 90
            logging.info(f"BATCH ID {'.'* (w - 8 - len(self.BATCH.BATCH_ID))} {self.BATCH.BATCH_ID}")
            logging.info(f"PUID FILE {'.'* (w - 9 - len(self.BATCH.PUID_FILE))} {self.BATCH.PUID_FILE}")
            logging.info(f"ITEM ID FILE {'.'* (w - 12 - len(self.BATCH.ITEM_ID_FILE))} {self.BATCH.ITEM_ID_FILE}")
            logging.info(f"REPORT FILE NAME {'.'* (w - 16 - len(self.BATCH.REPORT_FILE))} {self.BATCH.REPORT_FILE}")


            # AGGREGATING ITEMS FOR NEW BATCH
            # ---------------------------------------------------------------------------------------------------
            if True: # Testing just keeping this block for all loops not self.REDO or self.OAAT or self.RETRIED_LOOP:  # NEW BATCH
                logging.info("Executing SQLite query to get batch items...")
                self.BATCH.fillBatch(self.QUERY_STATUS, self.BATCH_SIZE, self.ORDER, table=self.SOURCE_TABLE)

                # BREAKING CONDITION
                if len(self.BATCH.ITEMS) == 0:
                    logging.info(f"No more items in the database with {self.QUERY_STATUS} import_status. Terminating Datashare utility.")
                    logging.info(f"Datashare Complete!\n\n{'='*115}")
                    return               


                # VOLUME CHECK POST-PROCESSING
                # ---------------------------------------------------------------------------------------------------
                oracleConfigs = [self.ORACLE_USER, self.ORACLE_PASSOWRD, self.ORACLE_HOST, self.ORACLE_PORT, self.ORACLE_SERVICE]
                self.BATCH.queryOracleVolumeInfo(oracleConfigs, self.SOURCE)

                # PERFORMS MISSING DATASET 
                # ---------------------------------------------------------------------------------------------------
                if self.SKIP_MISSING:
                    self.BATCH.separateSkipped()                    
                
                logging.info(f"The next {len(self.BATCH.ITEMS)} items are:\n")
                print(displayTabulatedItems(self.BATCH.ITEMS.keys(), 40, 3) + '\n')
            

                # WRITING FILES FOR data_share
                # ---------------------------------------------------------------------------------------------------
                with open(self.BATCH.ITEM_ID_FILE, 'w') as IIDfile, \
                    open(self.BATCH.PUID_FILE, "w") as PUIDfile:
                    for item_id, object in self.BATCH.ITEMS.items():
                        IIDfile.write(f"{item_id}\n")
                        PUIDfile.write(f"{object.PUID}\n")
                logging.info(f"List of Item IDs written in : {self.BATCH.ITEM_ID_FILE}")
                logging.info(f"List of PUIDs written in : {self.BATCH.PUID_FILE}")


            # RUNNING DATASHARE UTILITY
            # ---------------------------------------------------------------------------------------------------
            if len(self.BATCH.ITEMS) > 0:
                if self.OAAT or self.REDO:
                    self.datashareOAAT()
                else:
                    self.datashare()
            
            else:
                logging.warning("There was 0 items in the batch, therefore these items will be stepped over and labelled with MISSING DATASET REFERENCE")


            # UPDATING DATABASE
            # ---------------------------------------------------------------------------------------------------
            reportErrorLevel = self.BATCH.analyseReport(latest_ds_version=self.LATEST_DS, success_rate_threshold=self.SUCCESS_THRESHOLD)
            self.BATCH.setEnd()
            
            match(reportErrorLevel):
                
                # NO ERROR
                case 2001:
                    # SET BATCH STATUS
                    if self.OAAT:
                        self.BATCH.setStatus("SUCCESSFUL IN OAAT")

                        if self.ADAPTING_OAAT:
                            lastSuccessRates = self.getLastNSuccessRates(2) + [self.BATCH.SUCCESS_RATE]
                            try:
                                continueOaat: bool = sum(lastSuccessRates)/len(lastSuccessRates) != 1.0 

                            except TypeError as e:
                                continueOaat = True

                            self.setOaat(continueOaat)   # IF THE LAST 3 BATCHES HAVE 100% WILL STOP OAAT


                    elif self.REDO:
                        self.BATCH.setStatus("SUCCESSFUL IN OAAT (REDO)")
                        self.setRedo(False)

                    else:
                        self.BATCH.setStatus("SUCCESSFUL")

                    # IN CASE SERVER UNAVAILABLE
                    if self.RETRIED_LOOP:
                        self.setRetriedloop(False)

                    connection, cursor = self.connect()
                    if self.QUERY_STATUS == "NULL":
                        self.updateBatchTable(cursor)
                        self.updateItemsTable(cursor)
                        self.updateFailedItemsTable(cursor)
                    
                    elif self.QUERY_STATUS == "FAILED":
                        self.BATCH.setStatus("SUCCESSFUL FAILURE RECOVERY")
                        self.updateBatchTable(cursor)
                        self.failureRecoveryUpdate(cursor)

                    connection.commit()
                    connection.close()
                    
                    logging.info("Clearing memory")
                    self.cleanMemory()
                    self.COUNT += 1

                case 2501:
                    if self.REDO or self.OAAT:
                        logging.warning("The push did not pass the minimum success test while being processed One At a Time.")
                        logging.error("Please review the volumes")
                        return 
                    else:
                        logging.warning("The push did not pass the minimum success test. The batch will be resent in REDO mode")
                        self.REDO = True
                        continue
                
                # MISSING REPORT FILE
                case 2701:                    
                    if len(self.BATCH.ITEMS) > 0:
                        logging.warning(f"This batch failed due to a missing report file or disrupted IDSM connection. Entering REDO mode. Items in the batch will be processed one at a time." )
                        self.setRedo(True)
                    
                    else:
                        # EMPTY BATCH SCENARIO
                        connection, cursor = self.connect()
                    
                        self.BATCH.setStatus("FAILED WITH EMPTY BATCH")
                        self.updateBatchTable(cursor)
                        self.updateItemsTable(cursor)

                        connection.commit()
                        connection.close()      
                
                # IDSM ERROR
                case 2902:
                    logging.error(f"The IDSM connection between {self.SOURCE} -> {self.TARGET} is unavailable. Sleeping for 15 minutes and relaunching datashare...")
                    self.BATCH.setStatus("FAILED - IDSM CONNECTION INTERRUPTED")
                    connection, cursor = self.connect()
                    self.updateBatchTable(cursor)
                    connection.close()

                    if self.RETRIED_LOOP:
                        logging.error(f"The datashare loop was restarted and still cannot get an IDSM connection with {self.TARGET}. Stopping the loop")
                        return -1

                    else:
                        logging.info("Setting self.RETRIED_LOOP to True")
                        self.setRetriedloop(True)
                        for i in range(15, 0, -1):
                            logging.info(f"Datashare Loop restarting in {i} minutes.")
                            time.sleep(60)
                        self.datashareLoop()



    def simpleDatashareLoop(self) -> int:
        """
        Datashare enters a loop of sending objects to the data_share utility by leveraging subprocess.Popen(...)

        ### Parameters
            - None

        ### Returns
            - None
        """
        # PRINTING TITLE
        # ---------------------------------------------------------------------------------------------------
        width = 110
        title = "DATASHARE AUTOMATION"
        print(f"\n\n{'='*width}\n{' '* int((width -len(title))/2)}{title}\n{width*'='}\n\n")

        print("Using:")
        print(f"\tBatchSize: {self.BATCH_SIZE}")
        print(f"\tOAAT: {self.OAAT}")
        print(f"\tMODE: {self.MODE}")
        print(f"\tSkip Missing Datasets: {self.SKIP_MISSING}")
        print(f"\tQuery Status: {self.QUERY_STATUS}")
        print(f"\tOrder: {self.ORDER}")
        print(f"\tSource Table: {self.SOURCE_TABLE}")
        print(f"\tRouting IDSM: {self.TARGET_IDSM}")
        print(f"\tMinimum Success Threshold: {round(self.SUCCESS_THRESHOLD*100)} %")
        print(f"\tTransfer Option Set: {self.TRANSFER_OPTION_SET}")


        # INITIALIZATION
        # ---------------------------------------------------------------------------------------------------
        
        while True:
            
            # PRINTING HEADER
            # ---------------------------------------------------------------------------------------------------
            header = f"BATCH {self.COUNT} - RUN ONE ITEM AT A TIME" if self.REDO or self.OAAT else f"BATCH {self.COUNT} DETAILS"
            print(f"\n{'-'*width}\n{' '*int((width - len(header)) /2)}{header}\n{'-'*width}\n")
            

            # BATCH INITIALIZATION
            # ---------------------------------------------------------------------------------------------------
            
            start: datetime = datetime.now()
            startTimeStr = self.formatTime(start)    # Format: YYYY-MM-DD=HH-MM-SS
            
            if True: # testing this block always true not self.REDO or self.RETRIED_LOOP:
                prefix = "WSO_" if self.SOURCE_TABLE == "MigrationWSO" else ""
                suffix = "_FR" if self.QUERY_STATUS == "FAILED" else ""
                batch_id = f'{prefix}{self.SOURCE}_{startTimeStr}_{self.BATCH_SIZE}_{self.TARGET_IDSM}_{self.ORDER}{suffix}'
                puid_file = rf'Items\PUID\PUID_{batch_id}.txt'
                item_id_file = rf'Items\ItemID\item_list_{batch_id}.txt'
                report_file = rf'Reports\report_{batch_id}.txt'
                self.setBatch(Batch(batch_id, self.BATCH_SIZE, report_file, puid_file, item_id_file))
                

            
            # DISPLAY BATCH INFORMATION
            # ---------------------------------------------------------------------------------------------------
            w = 90
            logging.info(f"BATCH ID {'.'* (w - 8 - len(self.BATCH.BATCH_ID))} {self.BATCH.BATCH_ID}")
            logging.info(f"PUID FILE {'.'* (w - 9 - len(self.BATCH.PUID_FILE))} {self.BATCH.PUID_FILE}")
            logging.info(f"ITEM ID FILE {'.'* (w - 12 - len(self.BATCH.ITEM_ID_FILE))} {self.BATCH.ITEM_ID_FILE}")
            logging.info(f"REPORT FILE NAME {'.'* (w - 16 - len(self.BATCH.REPORT_FILE))} {self.BATCH.REPORT_FILE}")


            # AGGREGATING ITEMS FOR NEW BATCH
            # ---------------------------------------------------------------------------------------------------
            if True: # Testing just keeping this block for all loops not self.REDO or self.OAAT or self.RETRIED_LOOP:  # NEW BATCH
                logging.info("Executing SQLite query to get batch items...")
                self.BATCH.fillBatch(self.QUERY_STATUS, self.BATCH_SIZE, self.ORDER, table=self.SOURCE_TABLE)

                # BREAKING CONDITION
                if len(self.BATCH.ITEMS) == 0:
                    logging.info(f"No more items in the database with {self.QUERY_STATUS} import_status. Terminating Datashare utility.")
                    logging.info(f"Datashare Complete!\n\n{'='*115}")
                    return               
            
                
                logging.info(f"The next {len(self.BATCH.ITEMS)} items are:\n")
                print(displayTabulatedItems(self.BATCH.ITEMS.keys(), 40, 3) + '\n')
            

                # WRITING FILES FOR data_share
                # ---------------------------------------------------------------------------------------------------
                with open(self.BATCH.PUID_FILE, "w") as PUIDfile:
                    for puid in self.BATCH.ITEMS.keys():
                        PUIDfile.write(f"{puid}\n")
                logging.info(f"List of Item IDs written in : {self.BATCH.ITEM_ID_FILE}")
                logging.info(f"List of PUIDs written in : {self.BATCH.PUID_FILE}")


            # RUNNING DATASHARE UTILITY
            # ---------------------------------------------------------------------------------------------------
            if len(self.BATCH.ITEMS) > 0:
                if self.OAAT or self.REDO:
                    self.datashareOAAT()
                else:
                    self.datashare()
            
            else:
                logging.warning("There was 0 items in the batch, therefore these items will be stepped over and labelled with MISSING DATASET REFERENCE")


            # UPDATING DATABASE
            # --------------------------------------------------------------------------------------------------
            self.BATCH.setEnd()
            self.BATCH.skimReportForRate()

            if self.OAAT:
                self.BATCH.setStatus("SUCCESSFUL IN OAAT")

            else:
                self.BATCH.setStatus("SUCCESSFUL")

            connection, cursor = self.connect()
            if self.QUERY_STATUS == "NULL":
                self.updateBatchTable(cursor)
                self.updateWSOasSent(cursor)
            
            connection.commit()
            connection.close()
                    
            logging.info("Clearing memory")
            self.cleanMemory()
            self.COUNT += 1

                       

    def failureRecoveryLoop(self):

        # EXPLICITLY SETS FAILURE RECOVERY PARAMETERS
        self.SUCCESS_THRESHOLD = 0.0
        self.OAAT = True
        self.SKIP_MISSING: bool = False
        self.QUERY_STATUS: str = "FAILED"
        self.datashareLoop()
