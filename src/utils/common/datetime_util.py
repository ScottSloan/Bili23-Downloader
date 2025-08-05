from datetime import datetime

class DateTime:
    def time_str_from_timestamp(timestamp: int, format: str = "%Y/%m/%d %H:%M:%S"):
        return datetime.fromtimestamp(timestamp).strftime(format)