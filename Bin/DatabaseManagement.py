import logging
from DatabaseEditor.OracleEditor import OracleEditor
import sys
from pathlib import Path
import re
from datetime import datetime

class Callable:
    def __init__(self, display_name: str, function, oracle_editor: OracleEditor | None = None):
        self.name = display_name
        self.function = function
        self.editor = oracle_editor

    def __str__(self):
        return self.name

    def exectute(self):
        if self.editor == None:
            output = self.function()
        else:
            output = self.function(self.editor)

        return output


def getConfirmation(message: str) -> bool:
    inputVal = input(f"{message} [Y/N]: ")
    while True:
        if inputVal.strip().upper() == "Y":
            return True
        elif inputVal.strip().upper() == "N":
            return False
        else:
            inputVal = input("Input a valid answer [Y/N]: ")

def getInputLoop(valid_modes: dict[int, str]) -> int:
    
    validInputs = set(valid_modes.keys())
    while True:
        print()
        for i, element in valid_modes.items():
            print(f"\t{i}. {element}")
        print()
        userStrInput = input("Input: ")
        try:
            userInput = int(userStrInput.strip())
            if userInput not in validInputs:
                raise ValueError
            
            else:
                return userInput

        except ValueError:
            print("Invalid input. Please enter a valid input.")


def getPatternedInput(pattern_str: str) -> str:
    pattern = re.compile(pattern_str)
    while True:
        print()
        userStrInput = input("Input: ")
        if pattern.match(userStrInput):
            return userStrInput
        else:
            print("Please provide valid string input")


def itemDeltaProcedure(editor: OracleEditor):

    print("This procedure requires shifting all items from MigrationItems2 to MigrationItems. Ensure no processes are writing the database.")
    ui = getConfirmation("Do you want to shift all items to MigrationItems")
    if not ui:
        print("Aborted")
        return

    print("Shifting all items to MigrationItems")
    editor.shiftTables("ALL", "1:0", True)
    
    print("Which method for calculating date ranges do you want to use? ")
    options = { 1: "Use Calculated Start Date to Present",  # None-None
                2: "Overide Start Date to Present",         # Str-None
                3: "Provide Date Range",                    # Str-Str
                4: "Back"}
        
    ui = getInputLoop(options)
    if options[ui] == "Back":
        return

    match (int(ui)):
        case 1:
            modified, new = editor.getItems()

        case 2:
            while True:
                print("Input Start Date in the form YYYY-MM-DD HH:MM:SS ")
                start = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")
                
                startDatetime = datetime.strptime(start, r"%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                if startDatetime < datetime.now(): 
                    break
                else:
                    print(f"You input an invalid date string. The date must be prior to now: {now}. Provide a valid input.")

            modified, new = editor.getItems(start_date_range=start)

            
        case 3:
            while True:

                print("Input Start Date in the form YYYY-MM-DD HH:MM:SS ")
                start = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")

                print("Input End Date in the form YYYY-MM-DD HH:MM:SS ")
                end = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")

                # Check that ranges are valid
                startDatetime = datetime.strptime(start, r"%Y-%m-%d %H:%M:%S")
                endDatetime = datetime.strptime(end, r"%Y-%m-%d %H:%M:%S")

                if startDatetime < endDatetime: 
                    break
                else:
                    print(f"You input an invalid pair of date strings. The start date must be before the end date. Provide valid inputs.")
            
            modified, new = editor.getItems(start_date_range=start, end_date_range=end)

                
    ui = getConfirmation("Do you want to commit these changes")
    if ui:
        editor.updateDelta(modified, new)
    
    

def wsoDeltaProcedure(editor: OracleEditor):
    """
    Prompts user to input a date and  
    """
    
    print("Which valid workspace object do you want to add? ")
    options = {1: "UGCAMPTP",
               2: "HuskyECO",
               3: "CAEMesh",
               4: "CAEGeom",
               5: "CAESolution",
               6: "NXMotion",
               7: "NXSimulation",
               8: "CAEResults",
               9: "Back"}

    
    ui = getInputLoop(options)

    objectType = options[ui]
    if objectType == "Back":
        return

    print("Which method for calculating date ranges do you want to use? ")
    options = { 1: "Use Calculated Start Date to Present",  # None-None
                2: "Overide Start Date to Present",         # Str-None
                3: "Provide Date Range",                    # Str-Str
                4: "Back"}
        
    ui = getInputLoop(options)
    if options[ui] == "Back":
        return

    match (int(ui)):
        case 1:
            modified, new = editor.getWorkspaceObjects(objectType)

        case 2:
            while True:
                print("Input Start Date in the form YYYY-MM-DD HH:MM:SS ")
                start = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")
                
                startDatetime = datetime.strptime(start, r"%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                if startDatetime < datetime.now(): 
                    break
                else:
                    print(f"You input an invalid date string. The date must be prior to now: {now}. Provide a valid input.")

            modified, new = editor.getWorkspaceObjects(objectType, start_date_range=start)

           
        case 3:
            while True:

                print("Input Start Date in the form YYYY-MM-DD HH:MM:SS ")
                start = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")

                print("Input End Date in the form YYYY-MM-DD HH:MM:SS ")
                end = getPatternedInput(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")

                # Check that ranges are valid
                startDatetime = datetime.strptime(start, r"%Y-%m-%d %H:%M:%S")
                endDatetime = datetime.strptime(end, r"%Y-%m-%d %H:%M:%S")

                if startDatetime < endDatetime: 
                    break
                else:
                    print(f"You input an invalid pair of date strings. The start date must be before the end date. Provide valid inputs.")
            
            modified, new = editor.getWorkspaceObjects(objectType, start_date_range=start, end_date_range=end)

            
    ui = getConfirmation("Do you want to commit these changes")
    if ui:
        editor.updateWSO(modified, new)



def syncWSOStatus(editor: OracleEditor):
    while True:
        ui = input("Provide file path of your line-separated puids: ").replace('"', "")
        path = Path(ui)
        if path.exists():
            break

        else:
            print("The provided path does not extist. Please review input Please exclude double quotes.")

    editor.markFailedWSO(ui)
    confirmation = getConfirmation("Do you want to commit changes")

    if confirmation:
        editor.markFailedWSO(ui, confirmation)



def edgeCaseMark(editor: OracleEditor):
    """
    Gets user to input text file with all the puid to be marked out of scope
    
    """

    while True:
        ui = input("Provide file path of your line-separated puids: ").replace('"', "")
        path = Path(ui)
        if path.exists():
            break

        else:
            print("The provided path does not extist. Please review input Please exclude double quotes.")


    editor.markEdgeCase(ui)
    confirmation = getConfirmation("Do you want to commit changes")

    if confirmation:
        editor.markEdgeCase(ui, confirmation)


def shiftTables(editor: OracleEditor):
    options = { 1: "NULL", 
                2: "FAILED",
                3: "ALL"}

    ui = getInputLoop(options)
    status = options[ui]
    print("Input shifting proportion in the form P1:P2 where P1 is the ratio of items in MigrationItems and P2 is the ratio of items in MigrationItems2 ")
    proportion = getPatternedInput("[0-9]:[0-9]")

    editor.shiftTables(status, proportion)
    ui = getConfirmation("Do you want to commit the changes ")
    if ui:
        editor.shiftTables(status, proportion, ui)

    return False


def remapVolumes(editor: OracleEditor):
    oldPath = input("Please input old path to replace: ").replace('"', "")
    newPath = input("Please input new path to take its place: ").replace('"', "")

    editor.remapVolumePaths(oldPath, newPath)

    commit = getConfirmation("Do you want to commit changes")

    if commit:
        editor.remapVolumePaths(oldPath, newPath, commit)


def updateStatuses(editor: OracleEditor):

    print("Select table: ")
    options = { 1: "MigrationItems", 
                #2: "MigrationWSO",
                2: "Back"}
        
    ui = getInputLoop(options)
    table = options[ui]
    if table == "Back":
        return

    print("Select status change: ")
    options = { 1: "CORRUPT to FAILED for an aditional failure recovery pass", 
                2: "IN PROGRESS to NULL to reintialize status",
                3: "Back"}
    
    ui = getInputLoop(options)
    if options[ui] == "Back":
        return

    match(ui):
        case 1:
            oldStatus = "CORRUPT"
            newStatus = "FAILED"

        case 2:
            oldStatus = "IN PROGRESS"
            newStatus = "NULL"

    count = editor.getStatusCount(oldStatus, table=table)

    print(f"There are {count} objects with status {oldStatus} which would be modified to {newStatus}")
    ui = getConfirmation("Do you want to commit these changes")

    if ui:
        editor.changeImportStatus(oldStatus, newStatus, table=table)

    

def end() -> bool:
    return getConfirmation("Are you sure you want to quit")
     
def main() -> None:

    ui = getConfirmation(r"Do you want to use %MIG_HOME%\migration.db and %MIG_HOME%\Configuration\configuration.json")
    if ui: 
        oracleEditor = OracleEditor()

    else:
        database = input("Input database path: ")
        config = input("Input configuration.json path: ")
        oracleEditor = OracleEditor(database, config)


    options: dict[int, Callable] = {
               1: Callable("Initialize Tables", oracleEditor.createTables),
               #2: Callable("Populate Items for The First Time", oracleEditor.populateMigrationItems),
               2: Callable("Bulk Change Import Statuses", updateStatuses, oracleEditor),
               3: Callable("Perform an Item Delta", itemDeltaProcedure, oracleEditor),
               4: Callable("Perform a Workspace Object Delta", wsoDeltaProcedure, oracleEditor),
               5: Callable("Shift Tables", shiftTables, oracleEditor),
               6: Callable("Print Volume Configuration", oracleEditor.printVolumeInfo),
               7: Callable("Remap Volume Paths", remapVolumes, oracleEditor),
               8: Callable("Mark Migration Edge Cases", edgeCaseMark, oracleEditor),
               9: Callable("Sync Workspace Object Status via csv", syncWSOStatus, oracleEditor),
               10: Callable("Cancel", end)}

    loop = True
    while loop:
        userInput = getInputLoop(options)

        if options[userInput].name == "Cancel":
            if options[userInput].exectute():
                break

        else:

            options[userInput].exectute()
            loop = getConfirmation("Do you wish to perform any other changes")



if __name__ == "__main__":

    args = sys.argv
    if True: #"-log" in args:
        logging.basicConfig(level=logging.INFO,
                                format=" %(asctime)s [%(levelname)s] %(message)s",
                                datefmt='%H:%M:%S')

    
    main()

    
