from pathlib import Path
import re
import xml.etree.ElementTree as ET


def displayTabulatedItems(lov, width, cols) -> str:
    outputString = []
    for i, item in enumerate(lov):
        # Print the item padded to column width, without newline
        outputString += [str(item).ljust(width)]
        # Newline every `cols` items
        if (i + 1) % cols == 0:
            outputString += ['\n']
    return "".join(outputString)


def findDifference(file1, file2):
    file1Names = set()
    count1 = 0
    difference = set()


    with open(file1, "r") as file:
        for line in file:
            filename = line.split("\\")[-1].strip()
            file1Names.add(filename)
            count1 += 1
    
    print(f"There are {len(file1Names)} files in {file1}")
    
    with open(file2, "r") as fileTwo:
        for line in fileTwo:
            filename = line.split("\\")[-1].strip()
            
            if filename not in file1Names:
                print(f"{filename} is not in {file1}")
                difference.add(filename)

    print(f"There was a total of {len(difference)} of files missing")

    with open(r"D:\output.txt", "w") as output:
        for i in difference:
            output.write(i + "\n")


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

def printFSCLinesFromBackup(file: str):
    backupRoot = ET.parse(file).getroot()

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
        print(f'<volume id="{uid}" enterpriseid="xxxzy" priority="0" root"{path}" />')


def estimateThreadDist(n:int, sites: list = ["cabolsvetc1002","inchesvetc1002","lududsvetc1002","cnshasvetc1002","usmilsvetc1002"] ):
    import requests

    itemsRemaining = dict()
    for site in sites:
        data = requests.get(url = f"http://{site}:8000/summary").json()
        items = 0
        items += data["Items"]["NULL"]
        # items += data["SKIPPED"]
        items += data["Items"]["FAILED"]
        # items += data["INCONSISTENT SITE OWNERSHIP"]

        itemsRemaining[site] = items

    average = n / sum(itemsRemaining.values())
    print(f"An average of {average} items for the number of alloted threads")

    for site in sites:
        print(f"{site} should be allocated: {round(average * itemsRemaining[site],1)} threads")

if __name__ == "__main__":
    # printFSCLinesFromBackup(r"C:\Users\scastena.admin\Desktop\backup.xml")
    estimateThreadDist(10)