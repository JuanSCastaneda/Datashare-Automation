import re

class FailedItem:
    def __init__(self, item_id, batch_id, error, comment):

        self.ITEM_ID = item_id
        self.BATCH_ID = batch_id
        self.ERROR = error
        self.COMMENT = comment
        self.SUBCODE = None

        # SUMMARY: id93 in island1 failed with ERROR: ERROR:[11072] Xml attribute [data_file = mDOh8tfXADkqIB] not found in database for [id93:Form] element.
        
        if error == 11072:
            pattern = re.compile(r"(.*)\[(?P<error>.*)\](.*)\[(?P<reason>.*)\](.*)\[(?P<type>.*)\]")
            match = pattern.match(comment)

            if match:
                gd = match.groupdict()
                reason = gd['reason']
                
                self.SUBCODE = reason.split('=')[0].strip()
                print(self.SUBCODE)
                

if __name__ == "__main__":
    a = {"item_id":"4818150","batch_id":"lxdev10_2025-11-1=6-59-6_200","error":11072,"comment":"SUMMARY: id2801 in island190 failed with ERROR: ERROR:[11072] Xml attribute [relation_type] not found in database for [id2801:ImanRelation] element."}
    b = {"item_id":"4857470","batch_id":"lxdev10_2025-11-1=8-47-22_200","error":11072,"comment":"SUMMARY: id4508 in island178 failed with ERROR: ERROR:[11072] Xml attribute [data_file = TWOx9mVjADkqIB] not found in database for [id4508:Form] element."}
    classA = FailedItem(**a)
    classB = FailedItem(**b)
