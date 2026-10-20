import pyodbc
import sqlite3

class MSSQLEditor:
    def __init__(self):
        pass

    def PopulateViaMSSQL(sqliteDB, configfilename):
        # Collect Parameters
        DRIVER, SERVER, DATABASE, UID, PWD = AssignMSSQLConfigs(configfilename)

        sql_server_conn = pyodbc.connect(
        f'DRIVER={DRIVER};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'UID={UID};'
        f'PWD={PWD}'
        )

        sql_server_cursor = sql_server_conn.cursor()

        # --- Query SQL Server source table ---
        sql_server_cursor.execute("""
        SELECT
            item.pitem_id
            ,wso.pobject_name
            ,wso.pobject_type
            ,pomapp.plast_mod_date
        FROM [tc].[dbo].[PITEM] item
        JOIN [tc].[dbo].[PPOM_APPLICATION_OBJECT] pomapp on item.puid = pomapp.puid
        JOIN [tc].[dbo].[PWORKSPACEOBJECT] wso on item.puid = wso.puid
        JOIN PPOM_OBJECT po on po.puid = item.puid
        WHERE po.rowning_siteu is NULL;
        """)

        # --- Connect to SQLite ---
        sqlite_conn = sqlite3.connect(sqliteDB)
        sqlite_cursor = sqlite_conn.cursor()

        # --- Transfer data row by row ---
        for row in sql_server_cursor:
            item_id, object_name, object_type, last_mod_date = row
            
            # Convert SQL Server datetime to string (ISO format) if needed
            if last_mod_date:
                last_mod_date = last_mod_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_mod_date = None

            # Insert into SQLite
            sqlite_cursor.execute('''
                INSERT INTO MigrationItems 
                (item_id, object_name, object_type, last_mod_date)
                VALUES (?, ?, ?, ?)
            ''', (item_id, object_name, object_type, last_mod_date))

        # --- Finalize ---
        sqlite_conn.commit()

        # --- Cleanup ---
        sql_server_cursor.close()
        sql_server_conn.close()
        sqlite_conn.close()

        print("Data transfer from SQL Server to SQLite completed successfully.")

    def AssignMSSQLConfigs(configfilename):
        """
        Reads MSSQL configuration file to define the database's Driver, Server, Database
        UID, and Password

        Input:
        - Configuration Filename (by default MSSQL_Connect.config)
        
        Outputs:
        - Array [USER, PASSWORD, ORACLE_HOST, PORT, SERVICE_NAME]

        """
        configFile = open(configfilename, 'r')
        DRIVER = ''
        SERVER = ''
        DATABASE = ''
        UID = ''
        PWD = ''
        for line in configFile:
            if '<' in line or '>' in line:
                line = re.split("[<>]", line)
                if line[1] == "DRIVER":
                    DRIVER = line[2]
                elif line[1] == "SERVER":
                    SERVER = line[2]
                elif line[1] == "DATABASE":
                    DATABASE = line[2]
                elif line[1] == "UID":
                    UID = line[2]
                elif line[1] == "PWD":
                    PWD = line[2]
                

        configFile.close()
        if DRIVER == '' or SERVER == '' or DATABASE == '' or\
            UID == '' or PWD == '':
            raise EmptyParameter(f"You have an invalid entry in your {configfilename} \
                                file. Ensure there are no spaces between '<' and '>' symbols.\nPlease Review.")
    
        return DRIVER, SERVER, DATABASE, UID, PWD
