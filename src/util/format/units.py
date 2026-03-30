class Units:
    @classmethod
    def format_episode_duration(cls, duration: int):
        if duration is None:
            return "--:--"
        elif duration == 0:
            return ""
        else:
            return cls.format_duration(duration)
        
    @staticmethod
    def unformat_episode_duration(duration_str: str):
        parts = duration_str.split(":")
        parts = [int(part) for part in parts]

        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
        else:
            return 0

    @staticmethod
    def format_duration(duration: int):
        hours = int(duration // 3600)
        mins = int((duration - hours * 3600) // 60)
        secs = int(duration - hours * 3600 - mins * 60)

        if hours:
            return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2)
        else:
            return str(mins).zfill(2) + ":" + str(secs).zfill(2)
    
    @staticmethod
    def format_file_size(size: int):
        units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
        index = 0

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1
        
        return f"{size:.2f} {units[index]}"
    
    @staticmethod
    def format_bitrate(bitrate: int):
        if not bitrate:
            return ""
        
        units = ["bps", "Kbps", "Mbps", "Gbps", "Tbps", "Pbps", "Ebps"]
        index = 0

        while bitrate >= 1000 and index < len(units) - 1:
            bitrate /= 1000
            index += 1
        
        return f"{bitrate:.2f} {units[index]}"
    
    @staticmethod
    def format_frame_rate(frame_rate: float):
        if not frame_rate:
            return ""
        
        return f"{frame_rate:.1f} fps"
    
    @staticmethod
    def format_speed(speed: int):
        if not speed:
            return ""
        
        return f"{Units.format_file_size(speed)}/s"
    