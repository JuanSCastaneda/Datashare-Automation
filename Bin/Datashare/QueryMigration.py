from pathlib import Path
import logging
import sqlite3
import time
from datetime import datetime

from Datashare.Batch import *
from Datashare.Item import *
from Datashare.Exceptions import *


class QueryMigration:
    def __init__(self, database_path: str):

        if not Path(database_path).exists():
            raise FileNotFoundError(f"Could not find database at {database_path}, review its existence, and initialize via the Database Management Utility.")
        else:
            self.db = database_path

    def connect(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        A wrapper class for connecting to the database with extra verboseness
        
        ### Parameters
            - None
        ### Returns
            - Instance of sqlite3.connection
            - Instance of sqlite3.connection.cursor
            
        """
        logging.info(f"Connecting to {self.db}")
        N = 5
        for i in range(N):
            
            try:
                connection = sqlite3.connect(self.db, timeout=5)
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


    def insertDerefencedFiles(self, dereferenced_files: list[tuple[str]]):
        """
        Inserts or ignores:
            1. [insance_id, date_added, item_id, item_puid, ir_revision_id, ir_puid, relation_type, dataset_type, dataset_name, dataset_puid, file_puid] in DereferencedDatasets

            :param dereferenced_files: List of tuples to be input to an INSERT OR IGNORE query in the form [instance_id, item_id, item_puid, ir_revision_id, ir_puid, relation_type, dataset_type, dataset_name, dataset_puid, file_puid]
        """

        connection, cursor = self.connect()

        logging.debug(f"Inserting ~{len(dereferenced_files)} rows to DereferencedDatasets")
        cursor.executemany(f"""
            INSERT OR IGNORE INTO DereferencedDatasets
            (instance_id, date_added, item_id, item_puid, item_revision_id, item_revision_puid, relation_type, dataset_type, dataset_name, dataset_puid, imanfile_puid)
            VALUES
            (?,'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',?,?,?,?,?,?,?,?,?)
        """, dereferenced_files)

        connection.commit()
        connection.close()


    def insertMissingFiles(self, missing_files: list[tuple[str]]):
        """
        Inserts or ignores two inserts:
            1. [file_puid, volume_name, directory, filename, original_filename] in MissingImanfiles
        
        :param dereferenced_files: List of tuples to be input to an INSERT OR IGNORE query
        """

        connection, cursor = self.connect()
        logging.debug(f"Inserting ~{len(missing_files)} rows to MissingImanfiles")
        cursor.executemany(f"""
            INSERT OR IGNORE INTO MissingImanfiles
            (imanfile_puid, volume_name, directory, filename, original_filename)
            VALUES
            (?,?,?,?,?)
        """, missing_files)

        connection.commit()
        connection.close()


    def updateBatchTable(self, cursor: sqlite3.Cursor, batch: Batch) -> None:
        """
        ## Update Batch Table
        Inserts the following row in the MigrationBatches table:

        [Batch ID | Start Time | End Time | Status | List of Items File | Repor File | Size | Duration]

        :param cursor: SQLite3.cursor
        :param batch: Current Batch instance

        """
        
        start: str = batch.START.strftime("%Y-%m-%d %H:%M:%S")
        end: str = batch.END.strftime("%Y-%m-%d %H:%M:%S")
        
        logging.info(f"Batch Status: {batch.STATUS}")
        logging.info("Updating MigrationBatches Table... ")

        cursor.execute('''
        INSERT INTO MigrationBatches
        (batch_id, run_start_date, run_end_date, run_status, list_of_ids_filename, report_filename, batch_size, duration, success_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (batch.BATCH_ID, start, end, batch.STATUS, batch.ITEM_ID_FILE, batch.REPORT_FILE, batch.BATCH_SIZE, batch.DURATION, batch.SUCCESS_RATE))


    def updateWSOasSent(self, cursor: sqlite3.Cursor, batch: Batch, table: str) -> None:
        """
        ## Update Items Table
        Updates rows in the MigrationWSO table to add:

        [ Import Status | Batch ID | Datashare Date | Size | Duration]

        Where item.PUID is in batch.ITEMS.values()

        :param cursor: SQLite3.cursor
        :param batch: Current Batch instance
        :param table: Table to update

        """
        
        logging.info(f"Updating {len(batch.ITEMS)} Processed Items in The {table} Table...")
        

        cursor.executemany(f'''
                UPDATE {table}
                SET import_status = ?, batch_id = ?, data_share_date = ?, transfer_time = ? 
                WHERE puid = ?
            ''', [("SENT", batch.BATCH_ID , batch.END, item.DURATION, item.PUID)
                    for item in batch.ITEMS.values()])     


    def updateItemsTable(self, cursor: sqlite3.Cursor, batch: Batch, table: str) -> None:
        """
        ## Update Items Table
        Updates rows in the MigrationBatches table to add:

        [ Import Status | Batch ID | Datashare Date | Size | Duration]

        Where item.PUID is in batch.ITEMS.values()

        :param cursor: SQLite3.cursor
        :param batch: Current Batch instance
        :param table: Table to update

        """
        
        logging.info(f"Updating {len(batch.ITEMS)} Processed Items in The {table} Table...")

        cursor.executemany(f'''
                UPDATE {table}
                SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                WHERE puid = ?
            ''', [(item.STATUS, batch.BATCH_ID , batch.END, item.SIZE, item.DURATION, item.PUID)
                    for item in batch.ITEMS.values()])

        if n := len(batch.SKIPPED) > 0:
            logging.info(f"Updating {n} Skipped Items in {table} Table to have [import_status: MISSING DATASET REFERENCE]...")
            cursor.executemany(f'''
                        UPDATE {table}
                        SET import_status = ?, batch_id = ?, data_share_date = ? WHERE puid = ?''',
                        [(item.STATUS, batch.BATCH_ID , batch.END, item.PUID)
                        for item in batch.SKIPPED.values()])

        else:
            logging.info("This batch had no items missing essential datasets")           



    def updateFailedItemsTable(self, cursor: sqlite3.Cursor, batch: Batch, table: str = "FailedItems") -> None:
        """
        ## Update Failed Items Table
        Inserts the following row in the FailedItems table:

        [ Item ID | Object Type | Batch ID | Import Status | Error | Comment | Date | Puid ]

        :param cursor: SQLite3.cursor
        :param batch: Current Batch instance
        :param table: Table to update

        """
        failedItems = [(item.ITEM_ID, item.TYPE, batch.BATCH_ID, item.STATUS, item.ERROR, item.COMMENT, batch.END, item.PUID) \
                        for item in batch.ITEMS.values() if "FAILED" in item.STATUS]
        n = len(failedItems)
        if n > 0:
            logging.info(f"Appending {n} Items to The {table} Table...")
            cursor.executemany("""INSERT INTO FailedItems (item_id, object_type, batch_id, import_status, error, comment, data_share_date, puid)
                    VALUES (?,?,?,?,?,?,?,?)""", failedItems)

            logging.info(f"There was {n} failed item(s).")
        
        else:
            logging.info("This batch contained no failed items.")


    def failureRecoveryUpdate(self, cursor: sqlite3.Cursor, batch: Batch, table: str) -> None:
        """
        ## Updates Database
        ### Updates rows in the FailedItems table to change / delete:
        [ Batch ID | Import Status | Error | Comment | Date ]
        ### Updates

        Where item.PUID is in batch.ITEMS.values()

        ### Parameters
            - SQLite3.cursor
        
        ### Returns
            - None
        """
    
        corruptedItems: list[Item] = []
        recoveredItems: list[Item] = []
        for i in batch.ITEMS.values():
            if "FAILED" in i.STATUS:
                corruptedItems.append(i)
            elif "SUCCESS" in i.STATUS:
                recoveredItems.append(i)

        logging.info(f"Updating {len(corruptedItems)} Corrupt Items in The FailedItems Table...")
        cursor.executemany('''
                        UPDATE FailedItems
                        SET batch_id = ?, import_status = ?, error = ?, comment = ?, data_share_date = ? 
                        WHERE puid = ?
                    ''', [(batch.BATCH_ID, "CORRUPT", item.ERROR, item.COMMENT, batch.END, item.PUID)
                        for item in corruptedItems])
        
        
        logging.info(f"Deleting {len(recoveredItems)} Recovered Items in The FailedItems Table...")
        cursor.executemany("DELETE FROM FailedItems WHERE puid = ?", [(item.PUID,) for item in recoveredItems])

        logging.info(f"Updating {len(recoveredItems)} Recovered Items in The {table} Table...")
        cursor.executemany(f"""UPDATE {table}
                            SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                            WHERE puid = ?""",
                            [(item.STATUS, batch.BATCH_ID , batch.END, item.SIZE, item.DURATION, item.PUID)
                                for item in recoveredItems])
        
        logging.info(f"Updating {len(corruptedItems)} Corrupt Items in The {table} Table...")
        cursor.executemany(f"""UPDATE {table}
                            SET import_status = ?, batch_id = ?, data_share_date = ?, size = ?, transfer_time = ? 
                            WHERE puid = ?""",
                            [("CORRUPT", batch.BATCH_ID , batch.END, item.SIZE, item.DURATION, item.PUID)
                                for item in corruptedItems])
        

    def fetchNewBatchData(self, status:str, size: int, order: str, table: str, batch_id: str):

        connection, cursor = self.connect()
        command = ""

        # Applying status
        if status == "NULL":
            command = f"SELECT item_id, puid FROM {table} WHERE import_status is NULL"

        elif status == "SUCCESS" or status == "FAILED":
            command = f"SELECT item_id, puid FROM {table} WHERE import_status LIKE '{status}%'"
        
        else:
            raise InvalidInput("ERROR: Invalid status input to fillBatch(status=). Please use FAILED, SUCCESS, or NULL.")

        # Applying Order
        match order.upper():
            case "ASC":
                command += " ORDER BY ROWID ASC"
            case "DESC":
                command += " ORDER BY ROWID DESC"
            case _:
                pass

        # Applying Size
        if size != 0:
            command += f" LIMIT {size}"
                
        data = cursor.execute(command).fetchall()  

        logging.debug("Marking all items as 'IN PROGRESS'")
        cursor.executemany(f'''
            UPDATE {table}
            SET import_status = ?, batch_id = ?
            WHERE puid = ?
            ''', [("IN PROGRESS", batch_id, puid)
                for _, puid in data])     

        connection.commit()
        connection.close()

        return data
    

    def unmarkInProgress(self, cursor: sqlite3.Cursor, batch: Batch, table: str) -> None:
        """
        Given a batch instance, it will change the status of all objects in ITEMS back to NULL in the database
        
        :param batch: batch instance
        :param table: table name

        """
        cursor.executemany(f"UPDATE {table} SET import_status = NULL WHERE puid = ? AND import_status = 'IN PROGRESS'", 
                           [(item.PUID,) for item in batch.ITEMS.values()])

        cursor.executemany(f"UPDATE {table} SET import_status = NULL WHERE puid = ? AND import_status = 'IN PROGRESS'", 
                                   [(item.PUID,) for item in batch.SKIPPED.values()])