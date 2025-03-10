import os
import subprocess

from utils.config import Config

class FFmpeg:
    def __init__(self):
        pass

    def detect_location(self):
        if not Config.FFmpeg.path:
            cwd_path = self.get_cwd_path()
            env_path = self.get_env_path()
    
            if cwd_path:
                Config.FFmpeg.path = cwd_path

            if env_path and not cwd_path:
                Config.FFmpeg.path = env_path

    def check_available(self):
        self.detect_location()

        cmd = f""""{Config.FFmpeg.path}" -version"""

        if "ffmpeg version" in self.run_command(cmd, output = True):
            Config.FFmpeg.available = True

    def run_command(self, command: str, output = False):
        process = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

        if output:
            return process.stdout
    
    def get_env_path(self):
        ffmpeg_path = None
        path_env = os.environ.get("PATH", "")

        for directory in path_env.split(os.pathsep):
            possible_path = os.path.join(directory, self.ffmpeg_file_name)

            if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                ffmpeg_path = possible_path
                break

        return ffmpeg_path

    def get_cwd_path(self):
        ffmpeg_path = None

        possible_path = os.path.join(os.getcwd(), self.ffmpeg_file_name)
        
        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
            ffmpeg_path = possible_path

        return ffmpeg_path

    @property
    def ffmpeg_file_name(self):
        match Config.Sys.platform:
            case "windows":
                return "ffmpeg.exe"
            
            case "linux" | "darwin":
                return "ffmpeg"
