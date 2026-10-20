

class ItemDetails:
    def __init__(self, item_id: str, puid: str, batch_id: str, import_status: str, size: int, transfer_time: float):
        self.ITEM_ID = item_id
        self.PUID: str = puid
        self.BATCH_ID: str = batch_id
        self.STATUS: str = import_status
        self.SIZE: int = size
        self.DURATION: float = transfer_time
        self.TIME_FROM_START: float = None

    


    def getSpeed(self):
        try:
            return self.SIZE / self.DURATION
        except ZeroDivisionError:
            return 0
         

    def setTFS(self, time: float):
        self.TIME_FROM_START = time