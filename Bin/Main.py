from Datashare.Mercury import Mercury
import logging
import sys
import re
 
def main():
    args: list[str] = sys.argv
    mercury = Mercury()
 
    keyValPattern = re.compile(r"^-(?P<parameter>\w+)=(?P<argument>\w+)$")
    keyPattern = re.compile(r"^-(?P<parameter>\w+)$")
    for arg in args:
        if arg.startswith("-"):
 
            if match := keyValPattern.match(arg):
                gd = match.groupdict()
                key = gd["parameter"]
                value = gd["argument"]
 
            elif match := keyPattern.match(arg):
                gd = match.groupdict()
                key = gd["parameter"]
                value = None
 
            else:
                logging.warning(f"Invalid argument set: {arg}. Skipping...")
                continue
 
            match(key.upper()):
               
                case "SIZE":
                    mercury.setBatchSize(int(value))
               
                case "OAAT":
                    mercury.setOaat(True)
               
                case "ORDER":
                    mercury.setOrder(value.upper())
 
                case "MODE":
                    if value.upper() == "SIMPLE":
                        mercury.setMode("SIMPLE")
 
                case "STATUS":
                    if value.upper() == "FAILED":
                        mercury.setQueryStatus("FAILED")
               
                case "SKIPMISSING":
                    mercury.setSkipMissingDatasets(True)
               
                case "IDSM":
                    mercury.setTargetIDSM(value.upper())
               
                case "TABLE":
                    mercury.setSourceTable(value)    
 
                case "THRESHOLD":
                    value = float(value)
                    if value >= 0 and value <= 1:
                        mercury.setSuccessThreshold(value)    
 
                case "LATEST_DS":
                    mercury.setLatestDS(True)
 
                case "LOG":
                    mercury.setLog(True)
 
                case "TRANSFEROPTSET":
                    mercury.setTransferOptionSet(value)
 
                case "EXCLUDEFILES":
                    mercury.setExcludeFiles(True)
                   
                case _:
                    logging.warning(f"Invalid Paramter: {arg}")
 
 
    if mercury.MODE == "SIMPLE":
        mercury.simpleDatashareLoop()
        return
 
    else:
        if mercury.QUERY_STATUS == "FAILED":
            mercury.failureRecoveryLoop()
            return
        else:
            mercury.datashareLoop()
            return
   
 
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')
 
    main()
   
   
 
 
 