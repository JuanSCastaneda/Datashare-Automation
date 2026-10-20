import sqlite3
from datetime import datetime, timedelta
from re import split
from BatchResult.BatchesHistogram import BatchHistogram
from BatchResult.BatchDetails import BatchDetails
import numpy as np
import requests

class BatchResults:
    def __init__(self, url: str):
        self.BATCH_RESULTS: list[BatchDetails] = []
        self.TODAY = datetime.today()
        self.N = 0
        self.URL = url
        self.fillBatchResults()


    def fillBatchResults(self, status="SUCCESS") -> None:
        data = requests.get(f"{self.URL}/batchdetails").json()
        self.BATCH_RESULTS: list[BatchDetails] = [BatchDetails(**i) for i in data.values()]
        self.N: int = len(self.BATCH_RESULTS)

    
    def preProcessDailyThroughput(self) -> list[list, list]:
        """
        Preprocessing SQL queried data for plotting daily throughput 
        
        :param self:
        :returns: X, Y data sets for plotting the throughput of items
        :rtype: list[list(x), list(y)]
        """
        separated_by_day: dict[datetime, int] = dict()

        for i in self.BATCH_RESULTS:
            if "SUCCESS" in i.STATUS:

                if i.START.date() not in separated_by_day.keys():
                    separated_by_day[i.START.date()] = i.SIZE
                else:
                    separated_by_day[i.START.date()] += i.SIZE

        # Filling 0 Transfer Days
        start = min(separated_by_day)
        end = max(separated_by_day)
        j = start

        while j <= end:
            separated_by_day.setdefault(j,0)
            j += timedelta(days=1)

        separated_by_day = dict(sorted(separated_by_day.items()))   # forced sorted
        

        n_days_duration = {(k - start).days: v for k, v in separated_by_day.items()}
        x = list(n_days_duration.keys())
        y = list(n_days_duration.values())

        return x, y

    def removeOutliers(self, array, Nsigma):
        """
        Cleans data for a set of expected constant values. Removes points within N sigma.
        
        :param: Array, Nsigma
        :returns: X, Y data sets for plotting the throughput of items
        :rtype: list[list(x), list(y)]
        """
        i = 0
        while True:
            std = np.std(array)
            mean = np.mean(array)
            argmax = np.argmax(np.abs(np.array(array) - mean))
            if array[argmax] >= mean + Nsigma * std or array[argmax] <= mean - Nsigma * std:
                array.pop(argmax)
                i += 1
        
            else:
                break

        print(f"Removed {i} outliers")
        return array


    def preProcessTimePerItem(self, clean=False, rolling_avg= False, rolling_avg_limit= 0):
        """
        PreProcesses the data for time per item
        
        :param:
            clean: Boolean to determine if outliers should be removed\n
            rolling_avg: If a rolling average should be used\n
            rolling_avg_limit: The number of datapoints that should be used
        
        :returns: X, Y data sets for plotting the throughput of items
        :rtype: list
        """
        tpi = 0
        if rolling_avg:
            tpi  = 1 if self.N - rolling_avg_limit - 1 > 0 else 2           
        else:
            tpi = 2

        match tpi:
            case 1:
                time_per_item = [i.DURATION / i.SIZE for i in self.BATCH_RESULTS[self.N - rolling_avg_limit::]]
            case 2:
                time_per_item = [i.DURATION / i.SIZE for i in self.BATCH_RESULTS]
            case _:
                print("An error has occurred")
        
            
        if clean:
            time_per_item = self.removeOutliers(time_per_item, 2)

        return range(len(time_per_item)), time_per_item
    

    def preProcessHistorgram(self, bins: int) -> list[BatchHistogram]:
        durations = dict()
        batchHists = []
        for i in self.BATCH_RESULTS:
            if i.SIZE in durations.keys():
                durations[i.SIZE] = np.append(durations[i.SIZE], i.DURATION)

            else:
                durations[i.SIZE] = np.array([i.DURATION])

        # Enforce Sort
        for k, v in sorted(durations.items()):
            batchHists.append(BatchHistogram(k, v, bins))

        return batchHists





