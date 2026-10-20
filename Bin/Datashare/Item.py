import logging
from datetime import datetime

class Item:
    def __init__(self, item_id: str, puid: str):
        self.ITEM_ID = item_id
        self.PUID = puid
        self.TYPE = ''
        self.STATUS = 'NOT FOUND IN REPORT'
        self.ERROR = 0
        self.COMMENT = ''
        self.TRANSACTION_ID = 0
        self.PASSED_VOLUME_CHECK = True
        self.SIZE: int = 0

        self.START: datetime = None
        self.END: datetime = None
        self.DURATION: float = None


    def addToSize(self, size_file: int) -> None:
        """
        Add to Size adds your input parameter to the self.SIZE attribute to define the overall storage occupied by
        an Item in a Volume.

        ### Parameter
            - file_size (integer): Size of the file that is a part of the item
        """
        try: 
            self.SIZE += int(size_file)
        
        except ValueError:
            logging.warning(f"The file size you input was not an integer")


    # SETTERS
    # =================================================================================================================== #
    def setTransactionAttributes(self, obj_type: str, status: str, error: int, comment: str, transaction_id: int):
        self.TYPE = obj_type
        self.STATUS = status
        self.ERROR = error
        self.COMMENT = comment
        self.TRANSACTION_ID = transaction_id
    
    def setVolumeCheckStatus(self, check_status: bool) -> None:
        self.PASSED_VOLUME_CHECK = check_status

    def setStatus(self, new_status: str) -> None:
        self.STATUS = new_status

    def setStart(self) -> None:
        self.START = datetime.now()

    def setEnd(self) -> None:
        self.END = datetime.now()
        try:
            self.DURATION = round((self.END - self.START).total_seconds(), 2)
            
        except TypeError:
            self.DURATION = None
