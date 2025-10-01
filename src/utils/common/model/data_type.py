class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0

class Command:
    def __init__(self):
        self.command = []

    def add(self, command: str):
        self.command.append(command)

    def clear(self):
        self.command.clear()

    def format(self):
        return " && ".join(self.command)

class Process:
    output: str = None
    return_code: int = None

class CommentData:
    def __init__(self):
        self.start_time: int = 0
        self.end_time: int = 0
        self.text: str = ""
        self.width: int = 0
        self.row: int = 0
