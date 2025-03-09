class ThreadEvent:
    def __init__(self):
        self.event = False

    def set(self):
        self.event = True

    def is_set(self):
        return self.event

    def clear(self):
        self.event = False