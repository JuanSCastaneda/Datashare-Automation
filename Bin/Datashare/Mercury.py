"""
Mercury serves as the central object to iterate through the database and send packages (batches)
of Items to Teamcenter's data_share utility. It's responsibility is to catch errors, record results,
and send objects between source and target sites.

"""

import re
import subprocess 
import time
from Datashare.QueryTeamcenter import *
from Datashare.QueryMigration import *
from Datashare.Exceptions import *
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
        self.DBMgtSystem = data['DBMS'].upper().strip()

        user = data['User']
        password = data['Password']
        host = data['Host']
        port = data['Port']
        serviceName = data['ServiceName']
        match self.DBMgtSystem:
            case 'ORACLE':
                self.queryTeamcenter = QueryTeamcenter(user, password, host, port, serviceName, DatabaseManagementSystem.ORACLE)
            case 'MSSQL':
                self.queryTeamcenter = QueryTeamcenter(user, password, host, port, serviceName, DatabaseManagementSystem.MSSQL)

        databasePath = data['SQLiteDatabasePath']
        self.queryMigration: QueryMigration = QueryMigration(databasePath)

        # DATASHARE CONFIGURATIONS
        self.SOURCE: str = data['SourceSiteName']
        self.TARGET: str = data['TargetSiteName']
        
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


    def datashareOAAT(self) -> int:
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
                f'-optionset={self.TRANSFER_OPTION_SET}',
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

        return process.returncode
            

    def datashare(self) -> int:
        """
        Datashare performs the operation of sending the written files to Teamcenter's data_share utility,
        records the time stamp items were sent, and calculates their duration. 

        :Returns ReturnCode: passed as an int

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
                f'-optionset={self.TRANSFER_OPTION_SET}',
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

        return process.returncode
    
    # def getLastNSuccessRates(self, N: int) -> list[float]:

    #     connection, cursor = self.connect()
    #     data = [i[0] for i in cursor.execute(f"SELECT success_rate FROM MigrationBatches ORDER BY ROWID DESC LIMIT {N}").fetchall()]
    #     connection.close()

    #     return data

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
            startTimeStr = start.strftime("%Y-%m-%d %H:%M:%S")
            
            if True: # testing this block always true not self.REDO or self.RETRIED_LOOP:
                suffix = "_FR" if self.QUERY_STATUS == "FAILED" else ""
                batch_id = f'{self.SOURCE}_{startTimeStr}_{self.BATCH_SIZE}_{self.TARGET_IDSM}_{self.ORDER}{suffix}'
                puid_file = rf'Items\PUID\PUID_{batch_id}.txt'
                item_id_file = rf'Items\ItemID\item_list_{batch_id}.txt'
                report_file = rf'Reports\report_{batch_id}.txt'
                self.setBatch(Batch(batch_id, self.BATCH_SIZE, report_file, puid_file, item_id_file, self.queryTeamcenter, self.queryMigration))
                

            
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
                self.BATCH.fillBatch(self.QUERY_STATUS, self.BATCH_SIZE, self.ORDER, self.SOURCE_TABLE)

                # BREAKING CONDITION
                if len(self.BATCH.ITEMS) == 0:
                    logging.info(f"No more items in the database with {self.QUERY_STATUS} import_status. Terminating Datashare utility.")
                    logging.info(f"Datashare Complete!\n\n{'='*115}")
                    return               


                # VOLUME CHECK POST-PROCESSING
                # ---------------------------------------------------------------------------------------------------
                self.BATCH.itemVolumePrecheck()

                # PERFORMS MISSING DATASET 
                # ---------------------------------------------------------------------------------------------------
                if self.SKIP_MISSING:
                    self.BATCH.separateSkipped()             
                
                logging.info(f"The next {len(self.BATCH.ITEMS)} items are:\n")
                print(displayTabulatedItems(self.BATCH.ITEMS.keys(), 40, 3) + '\n')
            
                # WRITING FILES FOR data_share
                # ---------------------------------------------------------------------------------------------------
                self.writeInputFiles()

            # RUNNING DATASHARE UTILITY
            # ---------------------------------------------------------------------------------------------------
            
            try:
                returncode = 0
                if len(self.BATCH.ITEMS) > 0:
                    if self.OAAT or self.REDO:
                        returncode = self.datashareOAAT()
                    else:
                        returncode = self.datashare()
                
                if returncode != 0:
                    logging.error("data_share did not return code: 0.")
                    self.appendBatchLog(f"{self.BATCH.batchId} did not returned code {returncode} from data_share.")


            finally:
            # ANALYSE REPORT
            # ---------------------------------------------------------------------------------------------------
                try:
                    self.BATCH.analyseReport(latest_ds_version=self.LATEST_DS, success_rate_threshold=self.SUCCESS_THRESHOLD)
                    self.BATCH.setEnd()

                    if self.OAAT:
                        self.BATCH.setStatus("SUCCESSFUL IN OAAT")

                        # if self.ADAPTING_OAAT:
                        #     lastSuccessRates = self.getLastNSuccessRates(2) + [self.BATCH.SUCCESS_RATE]
                        #     try:
                        #         continueOaat: bool = sum(lastSuccessRates)/len(lastSuccessRates) != 1.0 
                        #     except TypeError as e:
                        #         continueOaat = True
                        #     self.setOaat(continueOaat)   # IF THE LAST 3 BATCHES HAVE 100% WILL STOP OAAT


                    elif self.REDO:
                        self.BATCH.setStatus("SUCCESSFUL IN OAAT (REDO)")
                        self.setRedo(False)

                    else:
                        self.BATCH.setStatus("SUCCESSFUL")

                    # IN CASE SERVER UNAVAILABLE
                    if self.RETRIED_LOOP:
                        self.setRetriedloop(False)

                    connection, cursor = self.queryMigration.connect()
                    if self.QUERY_STATUS == "NULL":
                        self.queryMigration.updateItemsTable(cursor, self.BATCH, self.SOURCE_TABLE)
                        self.queryMigration.updateFailedItemsTable(cursor, self.BATCH)
                        
                    
                    elif self.QUERY_STATUS == "FAILED":
                        self.BATCH.setStatus("SUCCESSFUL FAILURE RECOVERY")
                        self.queryMigration.failureRecoveryUpdate(cursor, self.BATCH, self.SOURCE_TABLE)

                    self.queryMigration.updateBatchTable(cursor, self.BATCH)
                    self.queryMigration.unmarkInProgress(cursor, self.BATCH, self.SOURCE_TABLE)

                    connection.commit()
                    connection.close()
                    
                    logging.info("Clearing memory")
                    self.cleanMemory()
                    self.COUNT += 1

                    
                except (EmptyReport, FileNotFoundError):
                    logging.error(f"The report from data_share was empty or not generated. Likely from an unavailable IDSM connection between {self.SOURCE} -> {self.TARGET} is unavailable. Sleeping for 15 minutes and relaunching datashare...")
                    self.appendBatchLog(f"Empty Report from data_share: {self.BATCH.REPORT_FILE}")
                    self.BATCH.setStatus("FAILED - EMPTY REPORT FILE")
                    connection, cursor = self.queryMigration.connect()
                    self.queryMigration.updateBatchTable(cursor, self.BATCH)
                    self.queryMigration.unmarkInProgress(cursor, self.BATCH, self.SOURCE_TABLE)
                    connection.commit()
                    connection.close()

                    if self.RETRIED_LOOP:
                        raise RuntimeError("Upon a restart after 15 minutes the datashare was still unable to send objects.")
                    
                    logging.info("Setting self.RETRIED_LOOP to True")
                    self.setRetriedloop(True)
                    for i in range(15, 0, -1):
                        logging.info(f"Datashare Loop restarting in {i} minutes.")
                        time.sleep(60)
                    self.datashareLoop()

                except FailedSuccessThreshold:
                    if self.REDO or self.OAAT:
                        logging.warning("The push did not pass the minimum success test while being processed One At a Time.")
                        logging.error("Please review the volumes")
                        return 
                    else:
                        logging.warning("The push did not pass the minimum success test. The batch will be resent in REDO mode")
                        self.REDO = True
                        continue                    


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
            startTimeStr = start.strftime("%Y-%m-%d %H:%M:%S")
            
            if True: # testing this block always true not self.REDO or self.RETRIED_LOOP:
                prefix = "WSO_" if self.SOURCE_TABLE == "MigrationWSO" else ""
                suffix = "_FR" if self.QUERY_STATUS == "FAILED" else ""
                batch_id = f'{prefix}{self.SOURCE}_{startTimeStr}_{self.BATCH_SIZE}_{self.TARGET_IDSM}_{self.ORDER}{suffix}'
                puid_file = rf'Items\PUID\PUID_{batch_id}.txt'
                item_id_file = rf'Items\ItemID\item_list_{batch_id}.txt'
                report_file = rf'Reports\report_{batch_id}.txt'
                self.setBatch(Batch(batch_id, self.BATCH_SIZE, report_file, puid_file, item_id_file, self.queryTeamcenter, self.queryMigration))
                

            
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
                self.BATCH.fillBatch(self.QUERY_STATUS, self.BATCH_SIZE, self.ORDER, self.SOURCE_TABLE)

                # BREAKING CONDITION
                if len(self.BATCH.ITEMS) == 0:
                    logging.info(f"No more items in the database with {self.QUERY_STATUS} import_status. Terminating Datashare utility.")
                    logging.info(f"Datashare Complete!\n\n{'='*115}")
                    return               
            
                
                logging.info(f"The next {len(self.BATCH.ITEMS)} items are:\n")
                print(displayTabulatedItems(self.BATCH.ITEMS.keys(), 40, 3) + '\n')
            

                # WRITING FILES FOR data_share
                # ---------------------------------------------------------------------------------------------------
                self.writeInputFiles()

            # RUNNING DATASHARE UTILITY
            # ---------------------------------------------------------------------------------------------------
            try:
                returncode = 0
                if len(self.BATCH.ITEMS) > 0:
                    if self.OAAT or self.REDO:
                        returncode = self.datashareOAAT()
                    else:
                        returncode = self.datashare()
                
                if returncode != 0:
                    logging.error("data_share did not return code: 0.")
                    self.appendBatchLog(f"{self.BATCH.batchId} did not returned code {returncode} from data_share.")
            
            # UPDATING DATABASE
            # --------------------------------------------------------------------------------------------------
            finally:
                try:
                    self.BATCH.setEnd()
                    self.BATCH.skimReportForRate()

                    if self.OAAT:
                        self.BATCH.setStatus("SUCCESSFUL IN OAAT")

                    else:
                        self.BATCH.setStatus("SUCCESSFUL")

                    connection, cursor = self.queryMigration.connect()
                    if self.QUERY_STATUS == "NULL":
                        self.queryMigration.updateWSOasSent(cursor, self.BATCH, self.SOURCE_TABLE)
                    
                    self.queryMigration.unmarkInProgress(cursor, self.BATCH, self.SOURCE_TABLE)
                    self.queryMigration.updateBatchTable(cursor, self.BATCH)

                    connection.commit()
                    connection.close()
                            
                    logging.info("Clearing memory")
                    self.cleanMemory()
                    self.COUNT += 1

                except (EmptyReport, FileNotFoundError):
                    logging.error(f"The report from data_share was empty or not generated. Likely from an unavailable IDSM connection between {self.SOURCE} -> {self.TARGET} is unavailable. Sleeping for 15 minutes and relaunching datashare...")
                    self.appendBatchLog(f"Empty Report from data_share: {self.BATCH.REPORT_FILE}")
                    self.BATCH.setStatus("FAILED - EMPTY REPORT FILE")
                    connection, cursor = self.queryMigration.connect()
                    self.queryMigration.updateBatchTable(cursor, self.BATCH)
                    self.queryMigration.unmarkInProgress(cursor, self.BATCH, self.SOURCE_TABLE)
                    connection.commit()
                    connection.close()

                    if self.RETRIED_LOOP:
                        raise RuntimeError("Upon a restart after 15 minutes the datashare was still unable to send objects.")

                    logging.info("Setting self.RETRIED_LOOP to True")
                    for i in range(15, 0, -1):
                        logging.info(f"Datashare Loop restarting in {i} minutes.")
                        time.sleep(60)
                    self.setRetriedloop(True)
                    self.simpleDatashareLoop()


    def failureRecoveryLoop(self):

        # EXPLICITLY SETS FAILURE RECOVERY PARAMETERS
        self.SUCCESS_THRESHOLD = 0.0
        self.OAAT = True
        self.SKIP_MISSING: bool = False
        self.QUERY_STATUS: str = "FAILED"
        self.datashareLoop()

    def appendBatchLog(self, message, filename=".\\batches.log"):
        now = datetime.now()
        with open(filename, "a") as file:
            file.write("="*150 + "\n")
            file.write(f"{now} - {message}\n")


    def writeInputFiles(self):
        logging.info("Writing input files...")
        with open(self.BATCH.ITEM_ID_FILE, 'w') as IIDfile, \
            open(self.BATCH.PUID_FILE, "w") as PUIDfile:
            for item_id, object in self.BATCH.ITEMS.items():
                IIDfile.write(f"{item_id}\n")
                PUIDfile.write(f"{object.PUID}\n")
            logging.info(f"List of Item IDs written in : {self.BATCH.ITEM_ID_FILE}")
            logging.info(f"List of PUIDs written in : {self.BATCH.PUID_FILE}")