import os
import subprocess
from configparser import RawConfigParser

class Config:
    class APP:
        name = "Bili23 Downloader"

        version = "1.42"
        version_code = 1420

        release_date = "2024/5/1"

    class Proxy:
        proxy = auth = False

        ip = port = uname = passwd = None
    
    class User:
        login = False
        uname = face = sessdata = None

    class Misc:
        show_episodes = 1

        auto_select = debug = check_update = False

        player_path = None

    class Download:
        path = None
        ffmpeg_path = None
        ffmpeg_available = False
        
        resolution = 80
        sound_quality = 30280
        codec = "HEVC"

        max_thread = 4
        max_download = 1

        show_notification = False

        add_number = False
        auto_delete = True

    class Type:
        VIDEO = 1
        BANGUMI = 2
    
    class Temp:
        download_window_pos = None

class Audio:
    audio_quality = None

    q_hires = False
    q_dolby = False

class Download:
    current_type = None
    
    download_list = []

class ConfigUtils:
    def __init__(self):
        self.path = os.path.join(os.getcwd(), "config.ini")

        self.config = RawConfigParser()
        self.config.read(self.path, encoding = "utf-8")

        self.load_config()
        self.create_download_dir()

        self.get_ffmpeg_path()

    def load_config(self):
        download_path = self.config.get("download", "path")

        # download
        Config.Download.path = download_path if download_path else os.path.join(os.getcwd(), "download")
        Config.Download.max_download = self.config.getint("download", "max_download")
        Config.Download.max_thread = self.config.getint("download", "max_thread")
        Config.Download.resolution = self.config.getint("download", "resolution")
        Config.Download.sound_quality = self.config.getint("download", "sound_quality")
        Config.Download.codec = self.config.get("download", "codec")
        Config.Download.show_notification = self.config.getint("download", "notification")
        Config.Download.add_number = self.config.getboolean("download", "add_number")
        Config.Download.auto_delete = self.config.getboolean("download", "auto_delete")

        # user
        Config.User.login = self.config.getboolean("user", "login")
        Config.User.face = self.config.get("user", "face")
        Config.User.uname = self.config.get("user", "uname")
        Config.User.sessdata = self.config.get("user", "sessdata")

        # proxy
        Config.Proxy.proxy = self.config.getboolean("proxy", "proxy")
        Config.Proxy.ip = self.config.get("proxy", "ip")
        Config.Proxy.port = self.config.get("proxy", "port")

        Config.Proxy.auth = self.config.getboolean("proxy", "auth")
        Config.Proxy.uname = self.config.get("proxy", "uname")
        Config.Proxy.passwd = self.config.get("proxy", "passwd")

        # misc
        Config.Misc.show_episodes = self.config.getint("misc", "show_episodes")
        Config.Misc.auto_select = self.config.getboolean("misc", "auto_select")
        Config.Misc.player_path = self.config.get("misc", "player_path")
        Config.Misc.check_update = self.config.getboolean("misc", "check_update")
        Config.Misc.debug = self.config.getboolean("misc", "debug")

    def create_download_dir(self):
        if not os.path.exists(Config.Download.path):
            os.makedirs(Config.Download.path)
    
    def get_ffmpeg_path(self):
        local_path = os.path.join(os.getcwd(), "ffmpeg.exe")

        path = local_path if os.path.exists(local_path) else "ffmpeg"

        Config.Download.ffmpeg_path = path

        process = subprocess.Popen(f'"{path}" -version', shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        process.wait()

        Config.Download.ffmpeg_available = True if "ffmpeg version" in str(process.stdout.read()) else False
    
    def save(self):
        with open(self.path, "w", encoding = "utf-8") as f:
            self.config.write(f)
    
conf = ConfigUtils()