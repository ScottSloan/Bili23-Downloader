from util.format.units import Units

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