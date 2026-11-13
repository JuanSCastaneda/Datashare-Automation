from enum import Enum
import oracledb
import logging

class DatabaseManagementSystem(Enum):
    ORACLE = 1
    MSSQL = 2

class QueryTeamcenter:
    def __init__(self, user: str, password: str, host: str, port: int, service_name: str, dbms: DatabaseManagementSystem):
        self.user: str = user
        self.password: str = password
        self.host: str = host
        self.port: int = port
        self.serviceName: str = service_name

        # SETS ALL QUERIES
        if dbms not in (DatabaseManagementSystem.ORACLE, DatabaseManagementSystem.MSSQL):
            raise TypeError("The type of database is not supported")
        else:
            self.managementSystem: Enum = dbms
            if dbms == DatabaseManagementSystem.ORACLE:
                self.connect = self.connectOracle
                self.queryItemVolumeDetails = self.queryItemVolumeDetailsOracle
                self.referencesTable = self.setReferenceTableOracle()

            elif dbms == DatabaseManagementSystem.MSSQL:
                self.connect = self.connectMSSQL
        

    def connectOracle(self):
        logging.debug("Connecting to the Oracle DB...")
        connection = oracledb.connect(
                    user=f'{self.user}',
                    password=f'{self.password}',
                    dsn=f'{self.host}:{self.port}/{self.serviceName}')
            
        cursor = connection.cursor()

        return connection, cursor

    def connectMSSQL(self):
        pass
        # connection = 
    
        # return connection, cursor

    def setReferenceTableOracle(self) -> str:
        """
        Checks if PREF_LIST has a column called pvalu_0. If yes then it will be used as the reflist table. If not PREF_LIST_0 will be used.

        :returns ReferenceTable: passed a string 
        """
        sql = """
            SELECT COLUMN_NAME
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = 'PREF_LIST'
            ORDER BY COLUMN_ID
        """
        connection, cursor = self.connect()
        result = cursor.execute(sql)
        connection.close()

        for row in result:
            if row[0].lower() == "pvalu_0":
                return "PREF_LIST"
            
        return "PREF_LIST_0"     


    def queryItemVolumeDetailsOracle(self, puids: list[str]) -> tuple[tuple[str]]:
        """
        Returns a tuple of tuples containing:
        [item_id, item_puid, ir_revision_id, ir_puid, relation_type, dataset_type, dataset_name, file_puid, volume_name, directory, filename, original_filename]
        
        :param puids: Flat list of puids
        :returns ResultSet: tuple of tuples with the above data order
        """

        connection, cursor = self.connectOracle()

        placeholder = ", ".join([f":{i+1}" for i in range(len(puids))])
        logging.debug(f"Querying volume data for {puids}")
        query = f"""
            SELECT item.pitem_id, item.puid itemrevision.pitem_revision_id, itemrevision.puid, relationtype.ptype_name,
            wsod.pobject_type, wsod.pobject_name, dataset.puid, imanfile.puid,
            volumes.PVOLUME_NAME, 
            volumes.PWNT_PATH_NAME || '\\' || imanfile.PSD_PATH_NAME, imanfile.PFILE_NAME, imanfile.PORIGINAL_FILE_NAME
            
                FROM PITEM item
                JOIN PITEMREVISION itemrevision
                    ON item.puid = itemrevision.RITEMS_TAGU
                JOIN PIMANRELATION relation
                    ON itemrevision.puid = relation.RPRIMARY_OBJECTU
                JOIN PIMANTYPE relationtype
                    ON relationtype.puid = relation.RRELATION_TYPEU
                JOIN PDATASET dataset
                    ON dataset.puid = relation.RSECONDARY_OBJECTU
                JOIN PWORKSPACEOBJECT wsod
                    ON dataset.puid = wsod.puid
                JOIN {self.referenceTable} reflist
                    ON dataset.puid = reflist.puid
                JOIN PIMANFILE imanfile
                    ON reflist.pvalu_0 = imanfile.puid
                JOIN PIMANVOLUME volumes
                    ON imanfile.RVOLUME_TAGU = volumes.puid
            WHERE item.puid IN ({placeholder})"""
    
        result = cursor.execute(query, puids).fetchall()
        connection.close()

        return result