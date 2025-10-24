class History:
    def __init__(self):
        self.history = []

    def add(self, url: str):
        self.history.append(url)

    def get(self):
        return self.history