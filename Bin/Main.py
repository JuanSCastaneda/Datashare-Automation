from Datashare.Mercury import Mercury
import logging 
import sys

def main():
    args: list[str] = sys.argv
    mercury = Mercury()
    
    for arg in args[1:]:
        if arg.startswith("-") and "=" in arg:
            key, value = arg[1:].split("=", 1)

            match(key.upper()):
                
                case "SIZE":
                    mercury.setBatchSize(int(value))
                
                case "OAAT":
                    mercury.setOaat(True if value.upper() == 'TRUE' else False)
                
                case "ORDER":
                    mercury.setOrder(value.upper())

                case "MODE":
                    if value.upper() == "SIMPLE":
                        mercury.setMode("SIMPLE")

                case "STATUS":
                    if value.upper() == "FAILED":
                        mercury.setQueryStatus("FAILED")
                
                case "SKIPMISSING":
                    mercury.setSkipMissingDatasets(True if value.upper() == 'TRUE' else False)
                
                case "IDSM":
                    mercury.setTargetIDSM(value.upper())
                
                case "TABLE":
                    mercury.setSourceTable(value)    

                case "THRESHOLD":
                    value = float(value)
                    if value >= 0 and value <= 1:
                        mercury.setSuccessThreshold(value)    

                case "LATEST_DS":
                    mercury.setLatestDS(True if value.upper() == 'TRUE' else False)

                case "LOG":
                    mercury.setLog(True)

                case "TRANSFEROPTSET":
                    mercury.setTransferOptionSet(value)
                    
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
    
    

