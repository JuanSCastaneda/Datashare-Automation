from fastapi import FastAPI
from MigCollector import MigCollector
from datetime import date, timedelta
import os

collector = MigCollector()

app = FastAPI()



@app.get("/")
def read_root():
    return collector.checkThreads()


@app.get("/status")
def read_status():
    return collector.checkNThreads()

@app.get("/details")
def read_details():
    return collector.threadBreakdown()


@app.get("/lastbatches/{n}")
def read_last_n_batches(n: int):
    return collector.queryLastNBatches(n)

@app.get("/summary")
def read_summary():
    return collector.querySummaryMetrics()

@app.get("/batchdetails")
def read_batchdetails():
    return collector.queryBatchDetails()

@app.get("/failuresurvey")
def read_failuresurvey():
    return collector.queryFailedItem()

@app.get("/summary/failures")
def read_failuresummary():
    return collector.queryFailureSummary()

@app.get("/error/{code}")
def read_failures_by_code(code):
    return collector.queryErrorsByCode(code)

@app.get("/error/11072/breakdown")
def read_11072_fails():
    return collector.get11072ModeCount()

@app.get("/throughput/{date_string}")
def read_throughput(date_string: str):
    return collector.getThroughput(date_string)



@app.get("/yesterday")
def read_throughput():
    td = date.today()
    td: date = td - timedelta(days=1)
    string = f"{td.year}-{td.month}-{td.day}"
    return collector.getThroughput(string)

