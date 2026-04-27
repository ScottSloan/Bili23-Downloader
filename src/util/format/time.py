from datetime import datetime


def _normalize_timestamp(timestamp: int | float):
    if abs(timestamp) >= 10_000_000_000:
        return timestamp / 1000

    return timestamp

class Time:
    @staticmethod
    def format_timestamp(timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S"):
        return datetime.fromtimestamp(_normalize_timestamp(timestamp)).strftime(fmt)
    
    @staticmethod
    def from_timestamp(timestamp: int):
        return datetime.fromtimestamp(_normalize_timestamp(timestamp))
    
    @staticmethod
    def from_string(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S"):
        return datetime.strptime(time_str, fmt)
    
    @staticmethod
    def format_srt_time(seconds: float):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))

        if ms == 1000:
            s += 1
            ms = 0
        if s >= 60:
            m += s // 60
            s = s % 60
        if m >= 60:
            h += m // 60
            m = m % 60
        
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    
    @staticmethod
    def format_ass_time_by_ms(ms: int):
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        centis = int(round((ms % 1000) / 10.0))

        if centis == 100:
            centis = 99

        return f"{hours:d}:{minutes:02d}:{seconds:02d}.{centis:02d}"
    
    @staticmethod
    def format_ass_time_by_seconds(seconds: float):
        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        s = int(seconds % 60)

        cs = int(round((seconds - int(seconds)) * 100))

        if cs == 100:
            s += 1
            cs = 0

        if s >= 60:
            m += s // 60
            s = s % 60

        if m >= 60:
            h += m // 60
            m = m % 60

        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
