from subprocess import run
import sqlite3
import os
import json
import re

class MigCollector:
    def __init__(self):
        try:
            migHome = os.environ['MIG_HOME']
            self.MIG_HOME = migHome
            with open(rf"{migHome}\Configuration\configuration.json") as file:
                data = json.load(file)
            self.DB = data['SQLiteDatabaseName']
            
        except KeyError:
            print("Invalid declaration of MigCollector. MIG_HOME not set.")


    def checkDatashareStatus(self):
        running: bool = False
        args = ["wmic",
                "process",
                "where",
                "(CommandLine like '%Main.py%' and name like 'python.exe')",
                "GET",
                "ProcessId,Name,CommandLine"]
        result = run(args, capture_output=True, text=True)
        
        foundDESC = False
        foundASC = False
        output = result.stdout.split('\n')
        for line in output:
            if 'Main.py' in line and 'DESC' in line:
                foundDESC = True
            
            elif 'Main.py' in line and 'ASC' in line:
                foundASC = True

        
        return {'Ascending Thread Status': foundASC,
                'Descending Thread Status': foundDESC}
    
    def checkThreads(self):
        args = ["wmic",
                "process",
                "where",
                "(CommandLine like '%Main.py%' and name like 'python.exe')",
                "GET",
                "ProcessId,Name,CommandLine"]
        result = run(args, capture_output=True, text=True)
        
        threads: dict = {
            "C01": False,
            "E01": False,
            "E02": False,
            "E03": False,
            "E04": False
        }
        output = result.stdout.split('\n')
        for line in output:
            if 'Main.py' in line:
                if "C01" in line:
                    threads["C01"] = True
                elif "E01" in line:
                    threads["E01"] = True
                elif "E02" in line:
                    threads["E02"] = True
                elif "E03" in line:
                    threads["E03"] = True
                elif "E04" in line:
                    threads["E04"] = True

        
        return threads
    

    def threadBreakdown(self):
        breakdown: dict = {
            "C01": False,
            "E01": False,
            "E02": False,
            "E03": False,
            "E04": False
        }

        try:
            breakdown["MIN_THREADS"] = int(os.environ["MIN_THREADS"].strip())
        except:
            breakdown["MIN_THREADS"] = "Unknown"

        args = ["wmic",
                "process",
                "where",
                "(CommandLine like '%Main.py%' and name like 'python.exe')",
                "GET",
                "ProcessId,Name,CommandLine"]
        result = run(args, capture_output=True, text=True)
        
        output = result.stdout.split('\n')
        
        pattern = re.compile(r"-(?P<switch>\w+)=(?P<value>\w+)")
        for line in output:
            if 'Main.py' in line:
                details = dict()
                parameters = line.split('"')
                for i in parameters:
                    if match := pattern.match(i):
                        gd = match.groupdict()
                        switch = gd["switch"]
                        value = gd["value"]

                        details[switch] = value

                match(details["idsm"]):
                    case "C01":
                        breakdown["C01"] = details
                    case "E01":
                        breakdown["E01"] = details
                    case "E02":
                        breakdown["E02"] = details
                    case "E03":
                        breakdown["E03"] = details
                    case "E04":
                        breakdown["E04"] = details

        return breakdown
    

    def checkNThreads(self):
        try:
            minThreads = int(os.environ["MIN_THREADS"].strip())
            
            count: int = 0
            args = ["wmic",
                    "process",
                    "where",
                    "(CommandLine like '%Main.py%' and name like 'python.exe')",
                    "GET",
                    "ProcessId,Name,CommandLine"]
            result = run(args, capture_output=True, text=True)
            

            output = result.stdout.split('\n')
            for line in output:
                if 'Main.py' in line:
                    count += 1
            
            if count >= minThreads:
                return "Minimum Thread Test: Pass"
            else:
                return "Minimum Thread Test: Failed"

        except:
            return "Failed to determinine minimum # threads"



                

    def queryLastNBatches(self, n: int) -> None:
            
        connect = sqlite3.connect(self.DB)
        cursor = connect.cursor()
        batch_data = [i for i in cursor.execute(f"SELECT batch_id, duration, run_status FROM MigrationBatchs ORDER BY ROWID DESC LIMIT {n}").fetchall()]
        
        batches: dict[str, dict]= {}
        for batID, duration, runStatus in batch_data:
            status = True if "OAAT" in runStatus else False
            batches[batID] = {"oaat": status, "duration": duration, "items": []}

        tables = [i[0] for i in cursor.execute("SELECT name FROM sqlite_master WHERE name LIKE 'MigrationItems%'").fetchall()]
        data = []
        for table in tables:

            query = f"""SELECT batch_id, item_id, puid, import_status, size, transfer_time
                            FROM {table} WHERE batch_id IN ({", ".join([f":{i+1}" for i in range(len(batches))])})"""

            data += cursor.execute(query, list(batches.keys())).fetchall()

        connect.close()

        # {batch_id}: {ooat: bool, items: [{item1}, {item2}, {item3}]}
        for line in data:
            batch_id, item_id, puid, import_status, size, transfer_time = line
            item_dict = {'item_id': item_id,
                         'puid': puid,
                         'batch_id': batch_id,
                         'import_status': import_status,
                         'size': size,
                         'transfer_time': transfer_time}

            if batch_id in batches.keys():
                batches[batch_id]["items"].append(item_dict)

        
        return batches
    

    def querySummaryMetrics(self):

        with sqlite3.connect(self.DB) as connection:
            cursor = connection.cursor()
            nNull = 0
            nSuccess = 0
            nFailed = 0
            nMissingDatasets = 0
            nNotFound = 0
            nEdgeCase = {"NULL":0, "SUCCESSFUL": 0, "FAILED": 0}
            nCorrupt = 0
            n = 0


            tables = [i[0] for i in cursor.execute("SELECT name FROM sqlite_master WHERE name LIKE 'MigrationItems%'").fetchall()]

            for table in tables:
                n += cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                nNull += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status is NULL").fetchone()[0]
                nSuccess += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status LIKE 'SUCCESS%'").fetchone()[0]
                nFailed += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE import_status LIKE 'FAILED%'").fetchone()[0]
                nMissingDatasets += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'MISSING DATASET REFERENCES%'").fetchone()[0]
                nNotFound += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'NOT FOUND IN REPORT%'").fetchone()[0]

                nEdgeCase["NULL"] += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'EDGE CASE - UNPROCESSED%'").fetchone()[0]
                nEdgeCase["SUCCESSFUL"] += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'EDGE CASE - SUCCESS%'").fetchone()[0]
                nEdgeCase["FAILED"] += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'EDGE CASE - FAILED%'").fetchone()[0]

                nCorrupt += cursor.execute(f"SELECT COUNT(*) from {table} WHERE import_status LIKE 'CORRUPT%'").fetchone()[0]



            avgRateWSO = cursor.execute("SELECT SUM(success_rate) / COUNT(*) FROM MigrationBatchs WHERE batch_id LIKE '%WSO_%'").fetchone()[0]
            
            workspaceObjects = cursor.execute("""
            SELECT 
                object_type,
                SUM(CASE WHEN import_status IS NULL THEN 1 ELSE 0 END) as 'nulls',
                SUM(CASE WHEN import_status = 'SENT' THEN 1 ELSE 0 END) as 'sents'

            FROM MigrationWSO GROUP BY object_type ORDER BY object_type ASC """).fetchall()
        

        other = n - sum((nNull, nSuccess, nFailed, nMissingDatasets, nNotFound, *nEdgeCase.values(), nCorrupt))

        items = {'NULL': nNull, 'SUCCESSFUL': nSuccess, 'FAILED': nFailed, "CORRUPT": nCorrupt, 'SKIPPED': nMissingDatasets, "EDGE CASES": nEdgeCase, "NOT FOUND IN REPORT": nNotFound, 'OTHER': other}
        wso = {"AVERAGE SUCESS RATE": avgRateWSO}
        totalSent = 0
        for row in workspaceObjects:
            objectType, nulls, sents = row
            totalSent += sents
            wso[objectType] = {"NULL": nulls, "SENT": sents}

        wso["CALCULATED FAILURES"] = int(totalSent * (1 - avgRateWSO))        

        return {"Items": items, "Workspace Objects" : wso}


    def get11072ModeCount(self):

        with sqlite3.connect(self.DB) as connection:
            modes = set()
            counts = dict()

            cursor = connection.cursor()

            comments = cursor.execute("SELECT comment FROM FailedItems WHERE error = 11072").fetchall()
            
            pattern = re.compile(r"(.*)\[(?P<error>.*)\](.*)\[(?P<reason>.*)\](.*)\[(?P<type>.*)\]")
            for comment in comments:
                if match := pattern.match(comment[0]):
                    gd = match.groupdict()
                    mode = gd['reason'].split('=')[0].strip()
                    modes.add(mode)


            for mode in modes:
                counts[mode] = cursor.execute(f"SELECT COUNT(*) FROM FailedItems WHERE error = 11072 AND comment LIKE '%{mode}%'").fetchone()[0]

            sorted_dict = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

        return sorted_dict

    def queryFailureSummary(self):
        with sqlite3.connect(self.DB) as connection:
            cursor = connection.cursor()

            counts: dict[int, int] = {int(k): int(v) for k, v in \
                                    cursor.execute("SELECT error, COUNT(error) FROM FailedItems GROUP BY error ORDER BY COUNT(error) DESC").fetchall()}

        return counts


    def queryErrorsByCode(self, code:int):
        errors = dict()
        with sqlite3.connect(self.DB) as connection:
            cursor = connection.cursor()

            counts: dict[int, int] = {i[0]: {"ItemID": i[1], "BatchID": i[2], "Status": i[3], "Comment": i[4]} for i in \
                cursor.execute(f"SELECT puid, item_id, batch_id, import_status, comment FROM FailedItems WHERE error = {code}").fetchall()}

        return counts


    def queryBatchDetails(self, status: str = 'SUCCESS'):
        if status not in ['FAILED', 'SUCCESS']:
            return {}
        
        with sqlite3.connect(self.DB) as connection:
            cursor = connection.cursor()
            data = cursor.execute(f"""SELECT batch_Id, run_start_date, run_end_date, run_status, batch_size, duration FROM MigrationBatchs
                                WHERE duration IS NOT NULL AND run_status LIKE '{status}%'""").fetchall()

        batchDetails = dict()
        for line in data:
            batch_Id, run_start_date, run_end_date, run_status, batch_size, duration = line
            batchDetails[batch_Id] = {'id': batch_Id,
                                      'run_start_date': run_start_date,
                                      'run_end_date': run_end_date,
                                      'status': run_status,
                                      'batch_size': batch_size,
                                      'duration': duration}
        
        return batchDetails
    
    def queryFailedItem(self):
        with sqlite3.connect(self.DB) as connection:
            cursor = connection.cursor()
            data = cursor.execute(f"""SELECT item_id, batch_id, error, comment FROM FailedItems WHERE import_status LIKE 'FAILED ON SITE%' OR import_status LIKE 'CORRUPT%'""").fetchall()
            connection.close()
            total = len(data)

        result: dict[int, list[dict]] = dict()
        result['total'] = total
        for line in data:
            item_id, batch_id, error, comment = line
            if error in result.keys():
                result[error].append({'item_id': item_id, 'batch_id': batch_id, 'error': error, 'comment': comment})
            else:
                result[error] = [{'item_id': item_id, 'batch_id': batch_id, 'error': error, 'comment': comment}]

        return result
        

    def getThroughput(self, date_string: str):

        result = dict()
        pattern= re.compile(r"(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)")

        if match := pattern.match(date_string):

            gd = match.groupdict()
            year = int(gd['year'])
            month = int(gd['month'])
            day = int(gd['day'])


            connection = sqlite3.connect(self.DB)
            cursor = connection.cursor()

            tables = [i[0] for i in cursor.execute("SELECT name FROM sqlite_master WHERE name LIKE 'MigrationItems%'").fetchall()]
            nSuccess = 0
            nFailed = 0
            nSkipped = 0
            nCorrupt = 0

            for table in tables:

                nSuccess += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_share_date LIKE '{year}-{month:02d}-{day:02d}%' AND import_status LIKE 'SUCCESS%'").fetchone()[0]
                nFailed += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_share_date LIKE '{year}-{month:02d}-{day:02d}%' AND import_status LIKE 'FAILED%'").fetchone()[0]
                nSkipped += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_share_date LIKE '{year}-{month:02d}-{day:02d}%' AND import_status LIKE 'MISSING%'").fetchone()[0]
                nCorrupt += cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_share_date LIKE '{year}-{month:02d}-{day:02d}%' AND import_status LIKE 'CORRUPT%'").fetchone()[0]

            

            result["Items"] = {"SUCCESS": nSuccess,
                    "FAILED": nFailed,
                    "SKIPPED": nSkipped}
            
            if nCorrupt > 0:
                result["Items"]["CORRUPT"] = nCorrupt

            # Workspace Objects
            nWSOSent = 0
            nWSOSent += cursor.execute(f"SELECT COUNT(*) FROM MigrationWSO WHERE data_share_date LIKE '{year}-{month:02d}-{day:02d}%' AND import_status LIKE 'SENT%'").fetchone()[0]
        
            connection.close()

            result["WorkspaceObjects"] = {"SENT": nWSOSent}
            
            
            return result
        
        else:
            return "Invalid Date String"
        


if __name__ == "__main__":
    a = MigCollector()
    print(a.queryFailedItem())