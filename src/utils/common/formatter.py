from utils.common.enums import ParseType

from utils.config import Config

class FormatUtils:
    @classmethod
    def format_episode_duration(cls, episode: dict, flag: int):
        match flag:
            case ParseType.Video:
                if "arc" in episode:
                    duration = episode["arc"]["duration"]
                elif "duration" in episode:
                    duration = episode["duration"]
                else:
                    return "--:--"

            case ParseType.Bangumi:
                if "duration" in episode:
                    duration = episode["duration"] / 1000
                else:
                    return "--:--"

        return cls.format_duration(duration)

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
    def format_bangumi_title(episode: dict, main_episode: bool = False):
        from utils.parse.bangumi import BangumiInfo

        if BangumiInfo.type_id == 2 and main_episode:
            return f"《{BangumiInfo.title}》{episode['title']}"
        
        else:
            if "share_copy" in episode:
                if Config.Misc.show_episode_full_name:
                    return episode["share_copy"]
                
                else:
                    for key in ["show_title", "long_title"]:
                        if key in episode and episode[key]:
                            return episode[key]

                    return episode["share_copy"]

            else:
                return episode["report"]["ep_title"]

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
