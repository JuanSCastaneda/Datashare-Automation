import sqlite3
import oracledb
import logging
from datetime import datetime
from .DatabaseEditor import DatabaseEditor
import json
import xml.etree.ElementTree as ET


class OracleEditor(DatabaseEditor):
    def __init__(self, sqlite3_database= r"migration.db", configuration_file= r"Configuration\configuration.json"):
        super().__init__(sqlite3_database)
        if self.MIG_HOME is not None:
            if self.MIG_HOME[-1] == '\\':
                self.CONFIG_FILE = self.MIG_HOME + configuration_file
            else:
                self.CONFIG_FILE = self.MIG_HOME + '\\' + configuration_file
        else:  
            self.CONFIG_FILE = configuration_file

        logging.info(f"Reading {self.CONFIG_FILE}")
        
        with open(self.CONFIG_FILE, "r") as file:
            data = json.load(file)

        # DATABASE MANAGEMENT SYSTEM VARIABLES
        self.USER = data['OracleUser']
        self.PASSWORD = data['OraclePassword']
        self.HOST = data['OracleHost']
        self.PORT = data['OraclePort']
        self.SERVICE = data['OracleService']

        logging.info(f"Connecting to {self.HOST}/{self.SERVICE}")


    def connectOracle(self) -> tuple[oracledb.Connection, oracledb.Cursor]:
        logging.info("Connecting to database...")
        
        connection = oracledb.connect(
            user=f'{self.USER}',
            password=f'{self.PASSWORD}',
            dsn=f'{self.HOST}:{self.PORT}/{self.SERVICE}'
        )

        cursor = connection.cursor()

        return connection, cursor


    def getWorkspaceObjects(self, object_type: str,
                            start_date_range: None | str = None,
                            end_date_range: None | str = None,
                            valid_types: tuple[str] = ("UGCAMPTP", "HuskyECO", "CAEMesh", "CAEGeom", "CAESolution", "NXMotion", "NXSimulation", "CAEResults"),
                            source_table: str = "MigrationWSO"):
        """
        Gathers workspace objects in the form:
        (object_name, object_name, object_type, last_mod_date, puid)

        Valid Input Types Include:
        UGCAMPTP, HuskyECO, CAEMesh, CAEGeom, CAESolution, NXMotion, NXSimulation

        """
        new = []
        modified = []

        # CHECKS
        # ================================================================================================================= #
        # INITIAL TYPE CHECK
        if object_type not in valid_types:
            logging.error(f"The input object type is invalid: {object_type}. It should be among {valid_types}")
            return modified, new
        
        try:

            liteConnection = sqlite3.connect(self.SQLITE3)
            liteCursor = liteConnection.cursor()
            existing = {k: v for k, v in liteCursor.execute(f"SELECT puid, last_mod_date FROM {source_table}").fetchall()}


            # GET START RANGE IF NONE
            if start_date_range is None:
                start_date_range = liteCursor.execute(f"SELECT MAX(last_mod_date) FROM {source_table}").fetchone()[0]

        finally:
            liteConnection.close()
        
        try:
            connection, cursor = self.connectOracle()
            query = f"""
                SELECT
                    wso.puid,
                    wso.pobject_name,
                    wso.pobject_type,
                    pomapp.plast_mod_date
                FROM PWORKSPACEOBJECT wso
                
                JOIN PPOM_APPLICATION_OBJECT pomapp ON wso.puid = pomapp.puid
                JOIN PPOM_OBJECT po ON po.puid = wso.puid

                WHERE po.rowning_siteu is NULL"""

            query += f"\n AND wso.pobject_type = '{object_type}'"

           

            if start_date_range is not None:
                query += f"\n AND pomapp.plast_mod_date >= TO_DATE('{start_date_range}', 'YYYY-MM-DD HH24:MI:SS')"
                logging.info(f"Using start date: {start_date_range}")
            else:
                logging.info("Using no start date range. Querying from earliest recorded object in Teamcenter.")

            if end_date_range is not None:
                query += f"\n AND pomapp.plast_mod_date <= TO_DATE('{end_date_range}', 'YYYY-MM-DD HH24:MI:SS')"
                logging.info(f"Using end date: {end_date_range}")
            else:
                logging.info("Using no end date range. Querying to latest recorded object in Teamcenter.")


            query += "\n ORDER BY pomapp.plast_mod_date ASC"

            logging.info(f"Querying database for all new {object_type}")
            
            logging.info(query)
            start = datetime.now()
            cursor.execute(query)
            logging.info(f"\nThe retrieval took {(datetime.now() - start).seconds} seconds")


            for line in cursor:
                puid, object_name, object_type, last_mod_date = line
                if puid not in existing.keys():
                    new.append((puid, object_name, object_type, last_mod_date, puid))
                else:
                    if last_mod_date != existing[puid]:
                        modified.append((puid, object_name, object_type, last_mod_date, puid))

            print(f"Found {len(new)} new {object_type}")
            print(f"Found {len(modified)} modified {object_type}")


        finally:
            connection.close()

        return modified, new



    def populateMigrationItems(self, scoped_types = ('CAEAnalysis', 'CAEGeometry', 'CAEModel', 'Item', 'EItem', 'SItem', 'MENCMachining', 'Document', 'HuskyECO')) -> None:
        """
        Populate Migration Items serves to query all items owned by a site, and insert:

        [ Item ID | Puid | Object Name | Object Type | Last Modification Date ]

        in the MigrationItems table.

        ### Paramters
            - None

        ### Returns 
            - None
        
        """
        # Connect to Oracle
        oracleConn = oracledb.connect(
            user=f'{self.USER}',
            password=f'{self.PASSWORD}',
            dsn=f'{self.HOST}:{self.PORT}/{self.SERVICE}'
        )
        
        oracleCursor = oracleConn.cursor()
        logging.info("Starting to query Oracle Database...")
        start = datetime.now()
        # Query Oracle
        oracleCursor.execute(f"""SELECT
            item.puid,
            item.pitem_id,
            wso.pobject_name,
            wso.pobject_type,
            pomapp.plast_mod_date
        FROM PITEM item
        JOIN PPOM_APPLICATION_OBJECT pomapp on item.puid = pomapp.puid
        JOIN PWORKSPACEOBJECT wso on item.puid = wso.puid
        JOIN PPOM_OBJECT po on po.puid = item.puid
        WHERE po.rowning_siteu is NULL AND 
        wso.pobject_type IN ({", ".join([f"'{i}'" for i in scoped_types])})
                    ORDER BY pomapp.plast_mod_date ASC 
        """)

        logging.info(f"\nThe query took {(datetime.now() - start).seconds} seconds")
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(self.SQLITE3)
        sqlite_cursor = sqlite_conn.cursor()

        # Loop through Oracle results and insert into SQLite
        logging.info("Starting to populate the SQLite Database...")
        start = datetime.now()
        for row in oracleCursor:
            # unpack Oracle row
            #object_id, object_type, status, error, comments, transaction_id, last_modification_date = row
            puid, item_id, object_name, object_type, last_mod_date = row
            # insert into SQLite
            sqlite_cursor.execute('''
                INSERT INTO MigrationItems 
                (puid, item_id, object_name, object_type, last_mod_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (puid, item_id, object_name, object_type, last_mod_date))

        oracleCursor.close()
        oracleConn.close()
        # Commit and close both connections
        sqlite_conn.commit()
        sqlite_conn.close()

        logging.info(f"\nThe population took {(datetime.now() - start).seconds} seconds")
        logging.info("Data copied successfully.")


    def getItems(self, start_date_range: None | str = None,
                      end_date_range: None | str = None,
                      source_table: str = "MigrationItems",
                      scoped_types = ('CAEAnalysis', 'CAEGeometry', 'CAEModel', 'Item', 'EItem', 'SItem', 'MENCMachining', 'Document', 'HuskyECO')) -> tuple[list[tuple[str]]]:
        """
        Performs Delta data operation. Uses the maximum last mod date from the last delta. Ensure that all columns have been migrated to one table
        Args:
            date_override: Date for last refresh in the form YYYY-MM-DD HH24:MI:SS
            source_table: Items containing all items [defaults to MigrationItems]
        Returns:
            modified: list of tuples of modified items
            new: list of tuples of new items
        """

        # GETTING LAST DELTA DATE
        # =================================================================================
        if start_date_range is None:
            with sqlite3.connect(self.SQLITE3) as liteConnection:
                liteCursor = liteConnection.cursor()
                tables = [i[0] for i in liteCursor.execute("SELECT name FROM sqlite_master WHERE name LIKE 'MigrationItems%'").fetchall()]
                subquery = " UNION ".join([f"SELECT MAX(last_mod_date) FROM {i}" for i in tables])
                start_date_range = liteCursor.execute(f"""
                    WITH joint (last_mod_date) AS ({subquery})
                    SELECT MAX(last_mod_date) FROM joint""").fetchone()[0]

        oracleConnection, oracleCursor = self.connectOracle()

        logging.info("Starting to query Oracle Database...")
        start = datetime.now()
        # Query Oracle
        query = f"""
            SELECT
                item.puid,
                item.pitem_id,
                wso.pobject_name,
                wso.pobject_type,
                pomapp.plast_mod_date
            FROM PITEM item
            JOIN PPOM_APPLICATION_OBJECT pomapp on item.puid = pomapp.puid
            JOIN PWORKSPACEOBJECT wso on item.puid = wso.puid
            JOIN PPOM_OBJECT po on po.puid = item.puid
            WHERE po.rowning_siteu is NULL 
            AND wso.pobject_type IN ({", ".join([f"'{i}'" for i in scoped_types])}) """
        
        if start_date_range is not None:
            query += f"\n AND pomapp.plast_mod_date >= TO_DATE('{start_date_range}', 'YYYY-MM-DD HH24:MI:SS')"
            logging.info(f"Using start date: {start_date_range}")
        else:
            logging.info("Using no start date range. Querying from earliest recorded object in Teamcenter.")

        if end_date_range is not None:
            query += f"\n AND pomapp.plast_mod_date <= TO_DATE('{end_date_range}', 'YYYY-MM-DD HH24:MI:SS')"
            logging.info(f"Using end date: {end_date_range}")
        else:
            logging.info("Using no end date range. Querying to latest recorded object in Teamcenter.")


        query += "\n ORDER BY pomapp.plast_mod_date ASC"
        logging.info("Executing:\n" + query)
        oracleCursor.execute(query)

        logging.info(f"\nThe query took {(datetime.now() - start).seconds} seconds")
        
        with sqlite3.connect(self.SQLITE3) as liteConnection:
            liteCursor = liteConnection.cursor()
            itemsInLite: dict[str, str] = {i[0]: i[1] for i in liteCursor.execute(f"SELECT puid, last_mod_date FROM {source_table}").fetchall()}
            puidsInLite: set[str] = set(itemsInLite.keys())

        modifiedItems = []
        newItems = []
        for row in oracleCursor:
            # unpack Oracle row
            #object_id, object_type, status, error, comments, transaction_id, last_modification_date = row
            puid, item_id, object_name, object_type, last_mod_date = row
            # insert into SQLite
            if puid in puidsInLite:
                if itemsInLite[puid] != last_mod_date:
                    modifiedItems.append((item_id, object_name, object_type, last_mod_date, puid))

            else:
                newItems.append((item_id, object_name, object_type, last_mod_date, puid))

        oracleConnection.close()

        print(f"There are {len(modifiedItems)} modified items from the delta sample")
        print(f"There are {len(newItems)} new items that would be added to the database")

        return modifiedItems, newItems


    

    def printVolumeInfo(self) -> None:
        """
        Prints the Volume Name and Path for every volume in the Teamcenter Database.
        ### Parameters:
            - None

        ### Returns
            - None

        """

        logging.info("Connecting to Oracle Database...")
        try:
            connection = oracledb.connect(
                user=f'{self.USER}',
                password=f'{self.PASSWORD}',
                dsn=f'{self.HOST}:{self.PORT}/{self.SERVICE}'
            )

            logging.info("Querying Volume Information...")
            cursor = connection.cursor()
            volumeInfo = cursor.execute("""SELECT PVOLUME_NAME, PWNT_PATH_NAME FROM PIMANVOLUME""").fetchall()
            connection.close()

            x = 20
            for line in volumeInfo:
                print(f"\t{(x - len(line[0]))*' '}{line[0]}: {line[1]}")

        except:
            logging.error("Could not connect to database. Please review database availability or configuration in %MIG_HOME%\\Configuration\\configuration.json")
        
    def changeVolumeNode(self, new_host: str, commit = False):
        """
        Updates volume node name to input """

        connection, cursor = self.connectOracle()
        data = cursor.execute("SELECT PUID, PVOLUME_NAME, PNODE_NAME FROM PIMANVOLUME").fetchall()
        puids = []
        for line in data:
            puid, name, node = line

            print(f"Volume {name.upper().strip()}'s node name would change from '{node.upper().strip()}' to new")

        if commit:
            cursor.executemany(f"UPDATE PIMANVOLUME SET PNODE_NAME = '{new_host}' WHERE PUID = ?", puids)
            connection.commit()

        connection.close()
        

    def remapVolumePaths(self, old_path_prefix: str, new_path_prefix: str, commit: bool = False) -> None:
        """
        Remap Volumes serves to edit the PIMANVOLUME table to change where the volumes are referencing

        ### Parameters:
            - old_path_prefix: The original path for the volume e.g. corp.huskyims.com\\ludud\\...
            - new_path_prefix: The path to replace the orignal  e.g. lubetnas02...
            - dry_run: By default True, change to false to commit the change after ensuring the paths are correct.

        ### Returns
            - None
        """
        connection, cursor = self.connectOracle()

        volumeInfo = cursor.execute("""SELECT PUID, PVOLUME_NAME, PWNT_PATH_NAME, PNODE_NAME FROM PIMANVOLUME""").fetchall()
        
        for line in volumeInfo:
            puid, name, path, _ = line
            path: str = path.lower()
            new_path = path.replace(old_path_prefix.lower(), new_path_prefix.lower())
            if path != new_path:
                logging.info(f"Would Update {name}: {path} --to--> {new_path}")

            if commit:
                logging.info(f"Updating {name}: {path} --to--> {new_path}")
                cursor.execute(f"""UPDATE PIMANVOLUME SET PWNT_PATH_NAME = '{new_path}' WHERE PUID = '{puid}'""")
                connection.commit()

        connection.close()


    def postRemapVolumeCheck(self, backup_xml: str, fms_master: str) -> None:
        """
        Cross references the backup.xml with FMS Master file for inconsistencies.
        
        ### Parameters:
            - None

        ### Returns
            - None
        """
        backupRoot = ET.parse(backup_xml).getroot()
        fmsRoot = ET.parse(fms_master).getroot()

        backup = dict()
        fms = dict()
        passTest = True

        # PARSING BACKUP XML
        for vol in backupRoot.findall("./volumeInfo"):
            path = ''
            uid = ''
            for child in vol:
                if child.tag == 'wntPath':
                    path = child.text.lower()
                elif child.tag == 'volumeUid':
                    uid = child.text
            backup[path] = uid

        for vol in backupRoot.findall("./transientVolumeInfo"):
            path = ''
            uid = ''
            for child in vol:
                if child.tag == 'wntPath':
                    path = child.text.lower()
                elif child.tag == 'transVolId':
                    uid = child.text
            backup[path] = uid
        

        # PARSING XML
        for vol in fmsRoot.findall("./fmsenterprise/fscgroup/fsc"):
            for child in vol:
                path = child.attrib['root'].replace('\\\\', '\\').lower()
                uid = child.attrib['id']
                fms[path] = uid

        for k, v in fms.items():
            try:
                if v != backup[k]:
                    logging.info(f"{v} has a misalignment between backup_info.xml, and the FMS_Master")
                    passTest = False

            except KeyError:
                logging.info(f"Backup does not have key {k}")
                passTest = False

        if passTest:
            logging.info("There were no issues flagged")


    def checkUNDOTBS1size(self):
        """
        Checks the size occupancy of UNDOTBS1 Table in dba_data_files. Increases size accordingly if required.

        ### Parameters:
            - None

        ### Returns
            - None
        """
        connection, cursor = self.connectOracle()
        logging.info("Checking UNDOTBS1's size allocation...")
        path, size, extensibility = cursor.execute("SELECT file_name, bytes, autoextensible FROM dba_data_files WHERE tablespace_name = 'UNDOTBS1'").fetchone()


        if extensibility =='NO' and size < 17179869184:
            logging.info("Upgrading UNDOTBS1's size allocation to 16GBs")
            cursor.execute(f"ALTER DATABASE DATAFILE '{path}' RESIZE 16g")
            connection.commit()
        else:
            logging.info("UNDOTBS1's size allocation is already greater than 16GBs")
        connection.close()
        

    def provideUpgradeSizeEst(self, write: bool = False) -> None:
        """
        Provides Size Estimate for Upgrade

        ### Parameters:
            - Write: Boolean value to determine whether to write the findings in a csv file

        ### Returns
            - None
        """
        connection, cursor = self.connectOracle()
        tables = ["PIMANEXPORTRECORD", "PPOM_STUB"]
        sizes = dict()
        totalSize: int = 0
        tables += [i[0] for i in cursor.execute("""SELECT ptname FROM PPOM_CLASS WHERE BITAND(pproperties, 8192) <> 0
                            UNION
                            SELECT ptname FROM PPOM_CLASS WHERE BITAND(pproperties, 32768) <> 0""").fetchall()]
        
        for j in tables:
            data = cursor.execute(f"""WITH cte1
                                    AS (SELECT table_name
                                        FROM user_tables
                                        WHERE table_name = '{j}'),
                                    cte2
                                    AS (SELECT SUM(blocks) * 8 / 1024 MB
                                        FROM dba_extents,
                                            cte1
                                        WHERE owner = (SELECT SYS_CONTEXT('userenv', 'current_schema')
                                            FROM dual)
                                            AND segment_name = cte1.table_name)
                                SELECT ROUND(SUM(mb), 0) FROM cte2 """).fetchone()
            logging.info(f"{j} occupies: {data[0]} MB")
            sizes[j] = data[0]
            totalSize += data[0]

        connection.close()
        print()
        logging.info(f"For a total size requirement estimate of {totalSize} MBs on {self.HOST}")

        if write:
            with open("sizeEstimate.csv", 'w') as file:
                file.write("TABLE,Current Size [MB],\n")
                for k,v in sizes.items():
                    file.write(f"{k},{v},\n")
                file.write(f"Total,{totalSize},")
                
    
    def checkOracleVersion(self) -> str:
        """
        Returns SQL Server Version

        ### Params:
            - None

        ### Returns:
            - String of version
        """
        connection, cursor = self.connectOracle()
        version = [i[0] for i in cursor.execute(f"SELECT * FROM v$version").fetchall()][0]
        logging.info(f"SQL Version: {version}")
        
        
        connection.close()

