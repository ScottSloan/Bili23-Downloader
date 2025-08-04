from datetime import datetime

class UniversalTool:
    def get_time_str_from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")
