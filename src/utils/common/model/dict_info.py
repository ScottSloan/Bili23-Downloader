class DictInfo(dict):
    def __init__(self):
        dict.__init__(self)

    def id_list(self, n: int = None):
        temp = list(self.values())

        return temp[n] if n is not None else temp
    
    def desc_list(self, n: int = None):
        temp = list(self.keys())

        return temp[n] if n is not None else temp
    
    def get_id(self, id: int):
        if id in self.id_list():
            return id
        else:
            if self.desc_list(0) == "自动":
                return self.id_list(1)
            else:
                return self.id_list(0)
    
    def check_id(self, id: int):
        if id in self.id_list():
            return id
        else:
            if len(self.id_list()):
                return self.id_list(0)
            else:
                return None