from subprocess import run
from time import sleep
import logging
import os
import sys


class TempClearer:
    def __init__(self, suffixes: str, interval: int = 60, temp_dir: str | None = None):
        
        try:
            self.tempDir = os.environ["TC_TMP_DIR"] if temp_dir is None else temp_dir
        
        except KeyError as e:
            print(e)
            logging.error("TC_TMP_DIR is not defined")
            return -1
        self.suffixes = suffixes.strip().split(',')
        self.interval = interval




    def deleteViaSuffix(self, suffix: str):
        logging.info(f"Deleting Files Ending In: {suffix}")
        run(["cmd.exe", "/c", "del", "*" + suffix])

    def checkCWD(self):
        cwb = os.getcwd()
        logging.info(f"Checking Current Working Directory: {cwb}")

        if cwb.lower() == self.tempDir.lower():
            logging.info("Aligned!")
            return True

        else:
            logging.error("The working directory is misaligned.")
            return False    

    def deleteLoop(self):

        while self.checkCWD():
            for suffix in self.suffixes:
                self.deleteViaSuffix(suffix)
            sleep((self.interval - 5)*60)
            for i in range(5,-1,-1):
                logging.info(f"Deleting files in: {i} mins...")
                sleep(60)
            
            
            


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')

    arguments = sys.argv
    tempClearer = None

    match(len(arguments)):
        
        case 2:
            suffixes = arguments[1]
            tempClearer = TempClearer(suffixes=suffixes)
        
        case 3:
            suffixes = arguments[1]
            interval = arguments[2]
            tempClearer = TempClearer(suffixes=suffixes, interval=int(interval))
        
        case 4:
            suffixes = arguments[1]
            interval = arguments[2]
            temp_dir = arguments[3]
            tempClearer = TempClearer(suffixes=suffixes, interval=int(interval), temp_dir=temp_dir)

        case _:
            logging.error("An invalid number of arguments. Should read [,Separated Suffixes (No Spaces)] [Interval] [Temp Dir]")
        
    if tempClearer is not None:
        tempClearer.deleteLoop()

    




