import datetime

from utils.config import Config

class FormatUtils:
    @classmethod
    def format_episode_duration(cls, duration: int):
        return cls.format_duration(duration) if duration else "--:--"

    @staticmethod        
    def format_duration(duration: int, show_hour: bool = False):
        hours = int(duration // 3600)
        mins = int((duration - hours * 3600) // 60)
        secs = int(duration - hours * 3600 - mins * 60)

        if show_hour or hours:
            return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2)
        else:
            return str(mins).zfill(2) + ":" + str(secs).zfill(2)
    
    @staticmethod
    def format_speed(speed: int):
        if speed > 1024 * 1024 * 1024:
            return "{:.1f} GB/s".format(speed / 1024 / 1024 / 1024)
        
        elif speed > 1024 * 1024:
            return "{:.1f} MB/s".format(speed / 1024 / 1024)
        
        elif speed > 1024:
            return "{:.1f} KB/s".format(speed / 1024)
        
        else:
            return "0 KB/s"

    @staticmethod
    def format_size(size: int):
        if not size:
            return "0 MB"
        
        elif size > 1024 * 1024 * 1024:
            return "{:.2f} GB".format(size / 1024 / 1024 / 1024)
        
        elif size > 1024 * 1024:
            return "{:.1f} MB".format(size / 1024 / 1024)
        
        else:
            return "{:.1f} KB".format(size / 1024)

    @staticmethod
    def format_bangumi_title(episode: dict, main_episode: bool):
        def get_share_copy():
            if "share_copy" in episode:
                return episode["share_copy"]
            else:
                return episode["report"]["ep_title"]
        
        from utils.parse.bangumi import BangumiInfo

        show_title = episode.get("show_title")

        if Config.Misc.show_episode_full_name or show_title.isnumeric():
            if BangumiInfo.type_id == 2 and main_episode:
                return f"《{BangumiInfo.series_title}》{episode['show_title']}"
            else:
                return get_share_copy()
        
        else:
            return episode.get("show_title", get_share_copy())

    @staticmethod
    def format_data_quantity(data: int):
        if data >= 1e8:
            return f"{data / 1e8:.1f}亿"
        
        elif data >= 1e4:
            return f"{data / 1e4:.1f}万"
        
        else:
            return str(data)

    @staticmethod
    def format_bandwidth(bandwidth: int):
        if bandwidth > 1024 * 1024:
            return "{:.1f} mbps".format(bandwidth / 1024 / 1024)
        
        else:
            return "{:.1f} kbps".format(bandwidth / 1024)

    @staticmethod
    def format_srt_line(start_time: float, end_time: float):
        def get_timestamp(time: float):
            ms = int((time - int(time)) * 1000)

            t = str(datetime.timedelta(seconds = int(time))).split('.')[0]

            return f"{t},{ms:03d}"

        return f"{get_timestamp(start_time)} --> {get_timestamp(end_time)}"
    
    @staticmethod
    def format_lrc_line(start_time: float):
        min = int(start_time // 60)
        sec = start_time % 60

        return f"{min:02}:{sec:04.1f}"
    
    @staticmethod
    def format_ass_timestamp(time: float):
        ms = int((time - int(time)) * 100)

        t = str(datetime.timedelta(seconds = int(time))).split('.')[0]

        return f"{t}.{ms:02d}"
    
    @staticmethod
    def format_xml_timestamp(time: int):
        return f"{time:.5f}"
