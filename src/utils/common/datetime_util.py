from datetime import datetime, timedelta

class DateTime:
    @classmethod
    def time_str_from_timestamp(cls, timestamp: int, format: str = "%Y/%m/%d %H:%M:%S"):
        return cls.from_timestamp(timestamp).strftime(format)
    
    @classmethod
    def time_str(cls, format: str = "%Y/%m/%d %H:%M:%S"):
        return cls.now().strftime(format)
    
    @staticmethod
    def from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp)
    
    @staticmethod
    def get_timestamp():
        return round(datetime.now().timestamp())
    
    @staticmethod
    def now():
        return datetime.now()
    
    @staticmethod
    def get_timedelta(datetime: datetime , delta_days: int):
        return round((datetime + timedelta(days = delta_days)).timestamp())

