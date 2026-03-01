from datetime import datetime

class Time:
    @staticmethod
    def format_timestamp(timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S"):
        return datetime.fromtimestamp(timestamp).strftime(fmt)
    