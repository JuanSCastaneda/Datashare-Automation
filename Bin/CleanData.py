import logging
from Datashare.DataCleaner import DataCleaner
logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

dc = DataCleaner("mtlab10", 124)
puids = dc.parseReportFile(r".\Bin\Datashare\report.csv")   
print(puids)
print(len(puids))