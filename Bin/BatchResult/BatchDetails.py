from re import split
from datetime import datetime

class BatchDetails:
    def __init__(self, id: str, run_start_date: str, run_end_date: str, status: str, batch_size: int, duration: int):
        self.ID: str = id
        self.START: datetime = datetime(*[int(i) for i in split("[-=]", run_start_date)])
        self.END: datetime = datetime(*[int(i) for i in split("[-=]", run_end_date)])
        self.STATUS: str = status
        self.SIZE: int = batch_size
        self.DURATION: int = duration
        self.OAAT: bool = True if "OAAT" in status else False
        
    def __str__(self):
        return f"ID: {self.ID}..... START: {self.START}.... OAAT: {self.OAAT}..... SIZE: {self.SIZE}..... DURATION: {self.DURATION}\n"
            