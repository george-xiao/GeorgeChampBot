import shelve

class OrderedShelve:
    '''
    Workaround to achieve ordered shelve; a dict is stored under db["dict"]
    Why is this workaround needed?
        Note that dbm implements a dict using internal hash-function that does not keep track of insertion order
        Since shelves is implemented using dbm, insertion order is not maintained
        To maintain insertion order, a dict is pickled in the shelve
    How does it work?
        Since dict maintains insertion order in Python3.7+, we can use it to bypass having to maintain order ourselves
    TODO: Find a non-hacky solution
    '''
    def __init__(self, database_path: str):
        self.shelve_db = None
        self.database_path = database_path

    def open(self) -> dict:
        self.shelve_db = shelve.open(self.database_path)
        db_dict = self.shelve_db.get("dict")
        if not db_dict:
            return {}
        return db_dict

    def close(self, modified_dict: dict = None):
        if modified_dict:
            self.__modify(modified_dict)
        self.shelve_db.close()

    def __modify(self, modified_dict: dict):
        self.shelve_db["dict"] = modified_dict
