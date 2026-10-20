from OracleEditor import OracleEditor
import logging
import subprocess
import os

def main() -> None:
    oracleEditor = OracleEditor()
    width = 115
    header = "Welcome to the Oracle Database Editor"
    print(f"{'='*115}\n{int((width - len(header))/2) * ' '}{header}\n{'='*115}\n\n")

    while True:
        print(" What would you like to do:")
        print("\t1. Print Current Volume Configuration\n\t2. Remap Volumes\n\t3. Perform Cross Check With backup.xml\n\t4. Exit\n\n")

        userResponse = input(" Please Insert Your Selection: ")
        match(userResponse.strip()):
            case '1':
                oracleEditor.printVolumeInfo()
            
            case '2':
                while True:
                    oldRoot = input(" Please paste the OLD root that you wish to replace: ").replace('"',"")
                    newroot = input(" Please paste the NEW root that you wish to replace with: ").replace('"',"")
                    
                    print(" Performing a dry run first")
                    oracleEditor.remapVolumes(oldRoot, newroot, dry_run=True)

                    userConfirmation = input(" Do you want to execute the change [Y/N]: ")
                    match(userConfirmation.strip().upper()):
                        case 'Y':
                            oracleEditor.remapVolumes(oldRoot, newroot, dry_run=False)
                            break
                        case _:
                            userReconfirmation = input(" Re-input roots? [Y/N]: ")
                            match(userReconfirmation.strip().upper()):
                                case 'Y':
                                    continue
                                case _:
                                    break

            case '3':
                while True:
                    command = "backup_xmlinfo -u=infodba -p=infodba -g=dba"
                    logging.info(f"Running backup_xmlinfo ...")
                    subprocess.run(args=command.split(' '))
                    logging.info("Done")
                    backupXML = oracleEditor.MIG_HOME + "\\Bin\\backup.xml"
                    fmsMaster = input(" Please paste the full path of the FMS Master file in %TC_ROOT%\\fsc\\: ").replace('"',"")
                    userCheckConfirmation = input("Perform check? [Y/N]: ")
                    
                    match(userCheckConfirmation.strip().upper()):
                        case 'Y':
                            try:
                                oracleEditor.postRemapVolumeCheck(backupXML, fmsMaster)

                                logging.info("Removing backup.xml")
                                os.remove(oracleEditor.MIG_HOME + "\\Bin\\backup.xml")

                                logging.info("Removing backup.dtd")
                                os.remove(oracleEditor.MIG_HOME + "\\Bin\\backup.dtd")
                                break
                            except FileNotFoundError as e:
                                print(f" Please review the file location of the {e.filename}.")
                                continue
                        case _:
                            break

            case '4':
                return

            case _:
                print(" That was an invalid entry. Please retry\n")

        userAnythingElse = input("\n Is there anything else you would like to do? [Y/N]: ")
        match(userAnythingElse.strip().upper()):
            case 'Y':
                continue
            case _:
                return
            
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format=" %(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')
    main()