import sqlite3
import logging
import os
from datetime import datetime
import re
from pathlib import Path

class DatabaseEditor:
    def __init__(self, sqlite3_database: str= 'migration.db'):
        # MAPPING TO MIG_HOME
        try:
            self.MIG_HOME = migHome = os.environ['MIG_HOME']
            logging.info(f"Using database in {migHome}\\{sqlite3_database}")
            
        except:
            logging.warning(f"Could not find MIG_HOME in Environment Variables. Defaulting to {sqlite3_database} in local directory.")
            self.MIG_HOME = None
        
        self.SQLITE3: str = self.MIG_HOME + '\\' + sqlite3_database if  self.MIG_HOME is not None else sqlite3_database

    def connect(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        connection = sqlite3.connect(self.SQLITE3)
        cursor = connection.cursor()
        return connection, cursor


    def createTables(self):
        """
        Creates AuditFiles, FailedItems, MigrationBatchs, MigrationItems, Volumes
        in SQLite3 Database
        """

        connect = sqlite3.connect(self.SQLITE3)
        cursor = connect.cursor()

        existing_tables = [i[0] for i in cursor.execute("SELECT tbl_name FROM sqlite_master WHERE type = 'table'").fetchall()]

        # if "AuditFiles" not in existing_tables:
        # logging.info("Creating AuditFiles Table...")
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS AuditFiles (
        #         puid	TEXT,
        #         status	TEXT,
        #         owning_site	TEXT,
        #         template	TEXT,
        #         directory	TEXT,
        #         subfolder	TEXT,
        #         filename	TEXT,
        #         PRIMARY KEY(puid)
        #         )
        #     ''')
        # else:
        #   logging.info("AuditFiles already exists. No action.")


        if "FailedItems" not in existing_tables:
            logging.info("Creating FailedItems Table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS FailedItems (
                    item_id	TEXT,
                    object_type	TEXT,
                    batch_id	TEXT,
                    import_status	TEXT,
                    error	INTEGER,
                    comment	TEXT,
                    data_share_date	TEXT,
                    puid	TEXT
                )
            '''            
            )
        else:
            logging.info("FailedItems already exists. No action.")

        if "MigrationBatchs" not in existing_tables:
            logging.info("Creating MigrationBatchs Table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS MigrationBatchs (
                    batch_Id	TEXT NOT NULL,
                    run_start_date	TEXT NOT NULL,
                    run_end_date	TEXT,
                    run_status	TEXT,
                    list_of_ids_filename	TEXT,
                    report_filename	REAL,
                    batch_size	INT,
                    duration	INTEGER,
                    PRIMARY KEY(batch_Id)
                )
            '''
            )
        else:
            logging.info("MigrationBatchs already exists. No action.")
        
        if "MigrationItems" not in existing_tables:
            logging.info("Creating MigrationItems Table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "MigrationItems" (
                    "item_id"	TEXT NOT NULL,
                    "object_name"	TEXT NOT NULL,
                    "object_type"	TEXT NOT NULL,
                    "last_mod_date"	TEXT NOT NULL,
                    "source_site"	TEXT,
                    "data_share_date"	TEXT,
                    "import_status"	TEXT,
                    "batch_id"	TEXT,
                    "puid"	TEXT NOT NULL UNIQUE,
                    "size"	INTEGER,
                    "transfer_time"	REAL,
                    PRIMARY KEY("puid")
                )
            ''')
        else:
            logging.info("MigrationItems already exists. No action.")


        if "MigrationItems2" not in existing_tables:
            logging.info("Creating MigrationItems2 Table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "MigrationItems2" (
                    "item_id"	TEXT NOT NULL,
                    "object_name"	TEXT NOT NULL,
                    "object_type"	TEXT NOT NULL,
                    "last_mod_date"	TEXT NOT NULL,
                    "source_site"	TEXT,
                    "data_share_date"	TEXT,
                    "import_status"	TEXT,
                    "batch_id"	TEXT,
                    "puid"	TEXT NOT NULL UNIQUE,
                    "size"	INTEGER,
                    "transfer_time"	REAL,
                    PRIMARY KEY("puid")
                )
            ''')
        else:
            logging.info("MigrationItems2 already exists. No action.")

        # if "Volumes" not in existing_tables:
        # logging.info("Creating Volumes Table...")
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS Volumes (
        #         volume_name	TEXT,
        #         number_files	INT,
        #         volume_size	INT,
        #         review_status	TEXT,
        #         volume_directory	TEXT,
        #         survey_filename	TEXT,
        #         impact_filename	TEXT,
        #         survey_date	TEXT,
        #         impact_date	TEXT,
        #         survey_duration	INT,
        #         impact_duration	INT
        #     )
        # ''')
        # else:
        #     logging.info("Volumes already exists. No action.")

        # if "TargetSnapshot" not in existing_tables:
        # logging.info("Creating TargetSnapshot Table...")
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS TargetSnapshot (
	    #         item_id	TEXT NOT NULL,
	    #         PRIMARY KEY("item_id")
        #     )""")
        # else:
        #     logging.info("TargetSnapshot already exists. No action.")
        

        # if "LastSnapshot" not in existing_tables:
        # logging.info("Creating LastSnapshot Table...")
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS LastSnapshot (
        #     Type	TEXT,
        #     Date	TEXT,
        #     Increment   INTEGER
        # )""")
        # else:
        #     logging.info("LastSnapshot already exists. No action.")

        if "MigrationWSO" not in existing_tables:
            logging.info("Creating MigrationWSO Table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "MigrationWSO" (
                "item_id"	TEXT NOT NULL,
                "object_name"	TEXT NOT NULL,
                "object_type"	TEXT NOT NULL,
                "last_mod_date"	TEXT NOT NULL,
                "source_site"	TEXT,
                "data_share_date"	TEXT,
                "import_status"	TEXT,
                "batch_id"	TEXT,
                "puid"	TEXT UNIQUE,
                "transfer_time"	REAL,
                PRIMARY KEY("puid")
                )
            """
            )
        else:
            logging.info("MigrationWSO already exists. No action.")


        connect.commit()
        connect.close()


    def restoreScope(self, table: str = "MigrationItems", items_in_scope: tuple[str] = ('CAEAnalysis', 'CAEGeometry', 'CAEModel',
                                                        'Item', 'EItem', 'SItem', 'MENCMachining',
                                                        'Document', 'HuskyECO')) -> None:
        """
        Limit to in scope items

        ### Parameters
            - items_in_scope: Optional
        
            
        ### Returns
            - None

        """

        connect = sqlite3.connect(self.SQLITE3)
        cursor = connect.cursor()

        logging.info("Querying Out of Scope Items")
        oosItemsCount = cursor.execute(f"""SELECT object_type, COUNT(*) FROM {table}
                                       WHERE object_type NOT IN  ({",".join(["?" for _ in items_in_scope])})
                                       AND import_status IS NOT NULL
                                       GROUP BY object_type""", items_in_scope).fetchall()  # ((type, count), )
        
        total = 0
        for type, count in oosItemsCount:
            logging.info(f"Marking {count} {type}(s) items as out of scope")
            total += count

        cursor.execute(f"""UPDATE {table}
                       SET import_status = 'OUT OF SCOPE' WHERE object_type NOT IN ({",".join(["?" for _ in items_in_scope])})
                       AND import_status IS NOT NULL""",
                       items_in_scope)

        logging.info(f"For a total of {total} Out of Scope Items marked")
        connect.commit()
        connect.close()


    def refreshTargetSnapshot(self, input_file: str):

        start = datetime.now()
        targetItemsIDs: set = set()
        logging.info("Parsing input file with item_id from production site")
        with open(input_file.replace('"',""), "r") as file:
            for line in file:
                targetItemsIDs.add(line.replace("\n", ""))

        end = datetime.now()
        logging.info(f"Parsing took {(end - start).total_seconds()} seconds")
        logging.info(f"There are {len(targetItemsIDs)} items on the target site")
        
        
        logging.info("Querying the source site for its items from TargetSnapshot...")
        start = datetime.now()

        connect = sqlite3.connect(self.SQLITE3)
        cursor = connect.cursor()
        sourceItemIds: set[str] = {i[0] for i in cursor.execute("SELECT item_id FROM TargetSnapshot").fetchall()}

        end = datetime.now()
        logging.info(f"Querying took {(end - start).total_seconds()} seconds")
        logging.info(f"There are {len(sourceItemIds)} items on the source site")

        difference = targetItemsIDs.difference(sourceItemIds)
        increment = len(difference)
        start = datetime.now()
        logging.info(f"Inserting {increment} newly transfered items from production into TargetSnapshot")
        cursor.executemany("INSERT INTO TargetSnapshot VALUES(?)", [(i,) for i in difference])
        end = datetime.now()
        logging.info(f"Inserting took {(end - start).total_seconds()} seconds")


        refreshType = "FULL" if len(sourceItemIds) == 0 else "SYNC"
        cursor.execute(f"INSERT INTO LastSnapshot VALUES('{refreshType}','{end.strftime("%d/%m/%Y %H:%M:%S")}',{increment})")
        connect.commit()
        connect.close()


    def restoreTransferedStatuses(self):

        connection = sqlite3.connect(self.SQLITE3)
        cursor = connection.cursor()

        countFailed = cursor.execute("""SELECT COUNT(*) FROM MigrationItems i
                                    JOIN TargetSnapshot ts ON ts.item_id = i.item_id
                                    WHERE i.import_status NOT LIKE 'SUCCESS%'""").fetchone()[0]
        
        countnull = cursor.execute("""SELECT COUNT(*) FROM MigrationItems i
                                    JOIN TargetSnapshot ts ON ts.item_id = i.item_id
                                    WHERE i.import_status IS NULL""").fetchone()[0]
        
        logging.info(f"There are {countFailed  + countnull} items who exist on the target site and who's import_status will switch to 'SUCCESS BY TARGET SYNC'")
        logging.info(f"Failed: {countFailed}")
        logging.info(f"Unprocessed: {countnull}")
        
        user = input("\nDo you want to commit these changes [Y/N]: ")

        if user.strip().upper() == "Y":
            now = datetime.now()
            logging.info("Filling unprocessed transferred items' import_status to 'SUCCESS BY TARGET SYNC'")
            cursor.execute(f""" WITH RESTORE AS (
                            SELECT i.item_id, i.import_status FROM MigrationItems i
                                JOIN TargetSnapshot ts ON ts.item_id = i.item_id
                            WHERE i.import_status IS NULL
                            ) 
                            UPDATE MigrationItems SET import_status = 'SUCCESS BY TARGET SYNC', data_share_date = '{str(now)}'
                            WHERE item_id IN (SELECT item_id FROM RESTORE)""")
            
            logging.info("Removing Items From FailedItems")
            cursor.execute(""" WITH toDelete AS (
                            SELECT i.item_id, i.import_status FROM MigrationItems i
                                JOIN TargetSnapshot ts ON ts.item_id = i.item_id
                            WHERE i.import_status NOT LIKE 'SUCCESS%'
                            ) 
                            DELETE FROM FailedItems
                            WHERE item_id IN (SELECT item_id FROM toDelete)""")
            
            logging.info("Replacing Failed transferred items' import_status to 'SUCCESS BY TARGET SYNC'")
            cursor.execute(f""" WITH toCorrect AS (
                            SELECT i.item_id, i.import_status FROM MigrationItems i
                                JOIN TargetSnapshot ts ON ts.item_id = i.item_id
                            WHERE i.import_status NOT LIKE 'SUCCESS%'
                            ) 
                            UPDATE MigrationItems SET import_status = 'SUCCESS BY TARGET SYNC', data_share_date = '{str(now)}'
                            WHERE item_id IN (SELECT item_id FROM toCorrect)""")
            connection.commit()
            connection.close()


    def shiftTables(self, status, proportion:str ="1:1", commit=False):
        connection: sqlite3.Connection = sqlite3.connect(self.SQLITE3)
        cursor: sqlite3.Cursor = connection.cursor()
        conditions = {"NULL": "WHERE import_status IS NULL",
                             "FAILED": "WHERE import_status LIKE 'FAILED%'",
                             "ALL": ""}

        n1 = int(cursor.execute(f"SELECT COUNT(*) FROM MigrationItems {conditions[status]}").fetchone()[0])
        n2 = int(cursor.execute(f"SELECT COUNT(*) FROM MigrationItems2 {conditions[status]}").fetchone()[0])

            
        print(f"MigrationItems has {n1} items with import status: {status}")
        print(f"MigrationItems2 has {n2} items with import status: {status}")
        largerTable = "MigrationItems" if n1 > n2 else "MigrationItems2"
        smallerTable = "MigrationItems" if n1 < n2 else "MigrationItems2"
        
        p1, p2 = [int(i) for i in proportion.split(":")]


        if p1 == 0:
            delta = int(n1)
            print(f"Moving {n1} items from MigrationItems to MigrationItems2")
            print(f"MigrationItems would now have 0 items with import_status: {status}")
            print(f"MigrationItems2 would now have {n2 + delta} items with import_status: {status}")
            if commit:
                self.moveQuery(connection, cursor, "MigrationItems", "MigrationItems2", status, delta)

        elif p2 == 0:
            delta = int(n2)
            print(f"Moving {n2} items from MigrationItems2 to MigrationItems")
            print(f"MigrationItems would now have {n1 + delta} items with import_status: {status}")
            print(f"MigrationItems2 would now have 0 items with import_status: {status}")
            if commit:
                self.moveQuery(connection, cursor, "MigrationItems2", "MigrationItems", status, delta)

        elif n2 == 0:
            delta = int((n1*p2) / (p1 + p2))
            print(f"Moving {delta} items from MigrationItems to MigrationItems2")
            print(f"MigrationItems would now have {n1 - delta} items with import_status: {status}")
            print(f"MigrationItems2 would now have {n2 + delta} items with import_status: {status}")
            if commit:
                self.moveQuery(connection, cursor, "MigrationItems", "MigrationItems2", status, delta)
            

        elif n1 / n2 > p1 / p2:
            delta = int((n1*p2 - p1*n2) / (p1 + p2))
            print(f"Moving {delta} items from MigrationItems to MigrationItems2")
            print(f"MigrationItems would now have {n1 - delta} items with import_status: {status}")
            print(f"MigrationItems2 would now have {n2 + delta} items with import_status: {status}")
            if commit:
                self.moveQuery(connection, cursor, "MigrationItems", "MigrationItems2", status, delta)

        elif n1 / n2 < p1 / p2:
            delta = int((p1*n2 - n1*p2) / (p1 + p2))
            print(f"Moving {delta} items from MigrationItems2 to MigrationItems")
            print(f"MigrationItems would now have {n1 + delta} items with import_status: {status}")
            print(f"MigrationItems2 would now have {n2 - delta} items with import_status: {status}")
            if commit:
                self.moveQuery(connection, cursor, "MigrationItems2", "MigrationItems", status, delta)

        else: 
            print(f"The specified proportions are already satisfied: {proportion}")

        
        connection.close()


    def moveQuery(self, connection, cursor, sourceTable, destinationTable, status, limit):
        conditions = {"NULL": "WHERE import_status IS NULL",
                     "FAILED": "WHERE import_status LIKE 'FAILED%'",
                     "ALL": ""}

        cursor.execute(f"""
            WITH rows2Add AS (
                SELECT 
                    item_id,
                    object_name,
                    object_type,
                    last_mod_date,
                    source_site,
                    data_share_date,
                    import_status,
                    batch_id,
                    puid,
                    size,
                    transfer_time
                FROM {sourceTable} {conditions[status]}
                ORDER BY ROWID
                LIMIT {limit}
                ) 
            INSERT INTO {destinationTable} 
            SELECT * 
            FROM rows2Add;
        """)

        print("Removing overlapping items")
        cursor.execute(f"DELETE FROM {sourceTable} WHERE puid IN (SELECT puid FROM {destinationTable})")
        connection.commit()
        n1Prime = cursor.execute(f"SELECT COUNT(*) FROM MigrationItems {conditions[status]}").fetchone()[0]
        n2Prime = cursor.execute(f"SELECT COUNT(*) FROM MigrationItems2 {conditions[status]}").fetchone()[0]
        print(f"MigrationItems now has {n1Prime} items with import_status: {status}")
        print(f"MigrationItems2 now has {n2Prime} items with import_status: {status}")


    def updateDelta(self, modified: list, new: list, source_table: str = "MigrationItems"):
            nUpdatedItems: int = len(modified)  
            nNewItem: int = len(new)
            with sqlite3.connect(self.SQLITE3) as liteConnection:
                liteCursor = liteConnection.cursor()
                logging.info(f"#Updated Modified Items since last refresh: {nUpdatedItems}")
                start = datetime.now()
                liteCursor.executemany(f"UPDATE {source_table} SET item_id=?, object_name=?, object_type=?, last_mod_date=?, import_status=NULL WHERE puid=?", 
                    modified)
    
                logging.info(f"Updating {source_table} took {(datetime.now() - start).seconds} seconds")
                start = datetime.now()
    
                logging.info(f"Removing modified items from FailedItems...")
                start = datetime.now()
                liteCursor.executemany("DELETE FROM FailedItems WHERE puid = ?", [(x[4],) for x in modified])
                logging.info(f"Removing modified items from FailedItems. took {(datetime.now() - start).seconds} seconds")
    
                # INSERTING NEW ITEMS IN MigrationItems
                logging.info(f"Inserting New Items into {source_table}: {nNewItem}")
                try:
                    liteCursor.executemany("""INSERT INTO MigrationItems 
                                            (item_id, object_name, object_type, last_mod_date, puid)
                                            VALUES (?, ?, ?, ?, ?)""", new)
                except sqlite3.IntegrityError as e:
                    logging.warning(f"Could not batch insert into {source_table}")
                    for newItem in new:
                        try:
                            liteCursor.execute("""INSERT INTO MigrationItems 
                                                    (item_id, object_name, object_type, last_mod_date, puid)
                                                    VALUES (?, ?, ?, ?, ?)""", newItem)
                        except sqlite3.IntegrityError as e2:
                            logging.warning(f"Could not add {newItem} due to uniqueness puid constraint. Still marking import status to NULL")
                            liteCursor.execute(f"UPDATE {source_table} SET import_status = NULL WHERE puid = '{newItem[4]}'", )
    
                            
                logging.info(f"\nInserting into {source_table} took {(datetime.now() - start).seconds} seconds")
    
                liteConnection.commit()
    
            logging.info(f"There was {nUpdatedItems} modified items from the delta sample")
            logging.info(f"There was {nNewItem} new items added to the database")


    def updateWSO(self, modified: list, new: list, source_table = "MigrationWSO"):
        """
        Param
            - modified: List of modified folders with inputs in the form: (object_name, object_type, last_mod_date, puid)
        """
        with sqlite3.connect(self.SQLITE3) as liteConnection:
            liteCursor = liteConnection.cursor()
            start = datetime.now()
            logging.info("Updating modified objects... ")
            liteCursor.executemany(f"UPDATE {source_table} SET item_id=?, object_name = ?, object_type=?, last_mod_date=?, import_status=NULL WHERE puid=?", 
                modified) # (puid, object_name, object_type, last_mod_date, puid)

            logging.info(f"Updating {source_table} took {(datetime.now() - start).seconds} seconds")
            start = datetime.now()

            logging.info(f"Removing modified items from FailedItems...")
            start = datetime.now()
            liteCursor.executemany("DELETE FROM FailedItems WHERE puid = ?", [(x[0],) for x in modified])
            logging.info(f"Removing modified items from FailedItems. took {(datetime.now() - start).seconds} seconds")

            # INSERTING NEW ITEMS IN MigrationItems
            try:
                liteCursor.executemany(f"""INSERT INTO {source_table} 
                                        (item_id, object_name, object_type, last_mod_date, puid) 
                                        VALUES (?, ?, ?, ?, ?)""", new)     # (puid, object_name, object_type, last_mod_date, puid)
            except sqlite3.IntegrityError as e:
                logging.warning(f"Could not batch insert into {source_table}")
                for newItem in new:
                    try:
                        liteCursor.execute(f"""INSERT INTO {source_table} 
                                                (item_id, object_name, object_type, last_mod_date, puid) 
                                                VALUES (?, ?, ?, ?, ?)""", newItem)
                    except sqlite3.IntegrityError as e2:
                        logging.error(f"Could not add {newItem} due to uniqueness puid constraint. Still marking import status to NULL")
                        liteCursor.execute(f"UPDATE {source_table} SET import_status = NULL WHERE puid = '{newItem[0]}'", )

                        
            logging.info(f"\nInserting into {source_table} took {(datetime.now() - start).seconds} seconds")

            liteConnection.commit()


    def markFailedWSO(self, puid_file_path, commit=False):
        puids = set()
        with open(puid_file_path, "r") as file:
            for line in file:
                puids.add(line.strip().replace('"', ""))

        try:
            connection, cursor = self.connect()

            cursor.execute("CREATE TEMP TABLE temp_successful (puid TEXT PRIMARY KEY)")
            cursor.executemany("INSERT INTO temp_successful (puid) VALUES (?)", ((puid,) for puid in puids))

            if not commit:
                successful = cursor.execute("SELECT COUNT(*) FROM MigrationWSO WHERE puid IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'").fetchone()[0]
                print(f"There are {successful} objects that were successfully sent that would be marked as 'SUCCESSFUL'")

                failed = cursor.execute("SELECT COUNT(*) FROM MigrationWSO WHERE puid NOT IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'").fetchone()[0]
                print(f"There are {failed} objects that were unsuccessfully sent that would be marked as 'FAILED'")


            else:
                successful = cursor.execute("SELECT COUNT(*) FROM MigrationWSO WHERE puid IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'").fetchone()[0]
                print(f"Marking {successful} objects as 'SUCCESSFUL'")
                cursor.execute("UPDATE MigrationWSO SET import_status = 'SUCCESSFUL' WHERE puid IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'")

                failed = cursor.execute("SELECT COUNT(*) FROM MigrationWSO WHERE puid NOT IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'").fetchone()[0]
                print(f"Marking {failed} objects as 'FAILED'")
                cursor.execute("UPDATE MigrationWSO SET import_status = 'FAILED' WHERE puid NOT IN (SELECT puid FROM temp_successful) AND import_status = 'SENT'")


        finally:
            if commit:
                connection.commit()
            connection.close()

    def markEdgeCase(self, puid_file_path, commit= False):
        puids = set()
        with open(puid_file_path, "r") as file:
            for line in file:
                puids.add(line.strip().replace('"', ""))


        try:
            connection, cursor = self.connect()

            cursor.execute("CREATE TEMP TABLE temp_edge_cases (puid TEXT PRIMARY KEY)")
            cursor.executemany("INSERT INTO temp_edge_cases (puid) VALUES (?)", ((puid,) for puid in puids))

            tables = [i[0] for i in cursor.execute("SELECT name FROM sqlite_master WHERE name LIKE 'MigrationItems%'").fetchall()]

            for table in tables:
                print()
                print(f"Reviewing {table}... ")
                if not commit:
                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status LIKE 'SUCCESS%' AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    print(f"{n} items in {table} were previously transferred successfully who's import_status would be marked 'EDGE CASE - SUCCESS' ")

                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE (import_status LIKE 'FAILED%' OR import_status = 'CORRUPT') AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    print(f"{n} items in {table} previously failed who's import_status would be marked 'EDGE CASE - FAILED' ")

                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status IS NULL AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    print(f"{n} items in {table} were never processed who's import_status would be marked 'EDGE CASE - UNPROCESSED' ")
                   

                else:
                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status LIKE 'SUCCESS%' AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    cursor.execute(f"UPDATE {table} SET import_status = 'EDGE CASE - SUCCESS' WHERE import_status LIKE 'SUCCESS%' AND puid IN (SELECT puid FROM temp_edge_cases)")
                    print(f"{n} items in {table} were previously transferred successfully who's import_status were marked 'EDGE CASE - SUCCESS' ")


                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE (import_status LIKE 'FAILED%' OR import_status = 'CORRUPT') AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    cursor.execute(f"UPDATE {table} SET import_status = 'EDGE CASE - FAILED' WHERE (import_status LIKE 'FAILED%' OR import_status = 'CORRUPT') AND puid IN (SELECT puid FROM temp_edge_cases)")
                    print(f"{n} items in {table} previously failed who's import_status were marked 'EDGE CASE - FAILED' ")

                    n = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status IS NULL AND puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                    cursor.execute(f"UPDATE {table} SET import_status = 'EDGE CASE - UNPROCESSED' WHERE import_status IS NULL AND puid IN (SELECT puid FROM temp_edge_cases)")
                    print(f"{n} items in {table} were never processed who's import_status were marked 'EDGE CASE - UNPROCESSED' ")

                    
            if not commit:
                n = cursor.execute(f"SELECT COUNT(*) FROM FailedItems WHERE puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                print(f"{n} items in FailedItems  who's import_status will be marked 'EDGE CASE - FAILED' ")
            else:
                n = cursor.execute(f"SELECT COUNT(*) FROM FailedItems WHERE puid IN (SELECT puid FROM temp_edge_cases)").fetchone()[0]
                cursor.execute(f"UPDATE FailedItems SET import_status = 'EDGE CASE - FAILED', error = -23 WHERE puid IN (SELECT puid FROM temp_edge_cases)")
                print(f"{n} items in FailedItems who's import_status were marked 'EDGE CASE - FAILED' ")
            

        finally:
            if commit:
                connection.commit()
            connection.close()


    def getItemIdFromErrorCode(self, code: int, limit:int = 50, table:str ="FailedItems"):
        """
        ### Code: Error code as an int
        ### limit: Limit the number of items queried from Table
        ### Table: Source table to query, FailedItems by default
        """
        connection, cursor = self.connect()
        data = [i[0] for i in cursor.execute(f"SELECT item_id FROM {table} WHERE error = {int(code)} LIMIT {limit}").fetchall()]
        connection.close()

        return data        

    def getStatusCount(self, status: str, table="MigrationItems") -> int:
        """
        Aggregate count of a selected status from a denoted table

        """
        status = status.upper()
        try:
            connection, cursor = self.connect()
            if status == "NULL":
                query = f"SELECT COUNT(*) FROM {table} WHERE import_status IS NULL"
            else:
                query = f"SELECT COUNT(*) FROM {table} WHERE import_status = '{status}'"

            output = cursor.execute(query).fetchone()[0]
            logging.info(f"Executing query: {query}")
        finally: 
            connection.close()

        return output


    def changeImportStatus(self, old_status: str, new_status: str, table="MigrationItems") -> None:
        """
        Method to rapidly update all items in a table from one status to another
        """

        try:
            connection, cursor = self.connect()
            if new_status.upper() == "NULL":
                query = f"UPDATE {table} SET import_status = NULL WHERE import_status = '{old_status}'"
            else:
                query = f"UPDATE {table} SET import_status = '{new_status}' WHERE import_status = '{old_status}'"

            logging.info(f"Executing query: {query}")
            cursor.execute(query)

        finally: 
            connection.commit()
            connection.close()


    # DEPRECATED
    # ====================================================================================================================
    def getShiftParams(self):
        statusDict = {1: "NULL", 
                      2: "FAILED",
                      3: "ALL"}

        for k,v in statusDict.items():
            print(f"{k}. {v}")

        valid = set(statusDict.keys())
        while True:
            try:
                value = input("Which status would you like to shift: ")
                value = int(value.strip())
                if value not in valid:
                    raise ValueError
                else:
                    break
                    
            except ValueError as ve:
                print("Invalid user input. Select a valid option from above.")
            
        status = statusDict[value]

        pattern = re.compile(r"[0-9]:[0-9]")
        while True:
            prop = input("Input shifting proportion in the form P1:P2 where P1 is the ratio of items in MigrationItems and P2 is the ratio of items in MigrationItems2: ").strip()
            if pattern.match(prop):
                proportion = prop
                break
            else:
                print("Invalid user input.")

        return status, proportion



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    


        


    



