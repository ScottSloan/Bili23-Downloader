import os

from utils.config import Config
from utils.common.enums import Platform

class FFEnv:
    @staticmethod
    def check_file(path: str):
        return os.path.isfile(path) and os.access(path, os.X_OK)
    
    @classmethod
    def get_env_path(cls):
        path_env = os.environ.get("PATH", "")

        for directory in path_env.split(os.pathsep):
            possible_path = os.path.join(directory, cls.ffmpeg_file())

            if cls.check_file(possible_path):
                return possible_path

    @classmethod
    def get_cwd_path(cls):
        possible_path = os.path.join(os.getcwd(), cls.ffmpeg_file())
        
        if cls.check_file(possible_path):
            return possible_path

    @classmethod
    def get_ffmpeg_path(cls):
        return {
            "env_path": cls.get_env_path(),
            "cwd_path": cls.get_cwd_path(),
        }

    @classmethod
    def detect(cls):
        ffmpeg_path = cls.get_ffmpeg_path()

        env_path, cwd_path = ffmpeg_path["env_path"], ffmpeg_path["cwd_path"]
        
        if not Config.Merge.ffmpeg_path:
            Config.Merge.ffmpeg_path = env_path if env_path else Config.Merge.ffmpeg_path
            Config.Merge.ffmpeg_path = cwd_path if cwd_path else Config.Merge.ffmpeg_path
        else:
            if not cls.check_file(Config.Merge.ffmpeg_path):
                Config.Merge.ffmpeg_path = cwd_path

    @staticmethod
    def check_availability():
        return not os.path.exists(Config.Merge.ffmpeg_path)
    
    @staticmethod
    def ffmpeg_file():
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return "ffmpeg.exe"
            
            case Platform.Linux | Platform.macOS:
                return "ffmpeg"