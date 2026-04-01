from util.format import Units, Time

from typing import Any

class StrFormatter:
    def __init__(self, data: Any):
        self.data = data

    def __str__(self):
        return str(self.data)
    
class DurationFormatter:
    def __init__(self, duration: int):
        self.duration = duration

    def __str__(self):
        return Units.format_episode_duration(self.duration)

class DateFormatter:
    def __init__(self, timestamp: int):
        self.timestamp = timestamp

    def __str__(self):
        if self.timestamp:
            return Time.format_timestamp(self.timestamp, "%Y-%m-%d")
        else:
            return ""