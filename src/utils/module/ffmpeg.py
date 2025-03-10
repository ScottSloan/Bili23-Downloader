import os
import subprocess

from utils.common.enums import DownloadOption, StreamType
from utils.common.data_type import DownloadTaskInfo, Command
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

    def merge_dash_video(self):
        pass

    def merge_flv_video(self):
        pass

    def get_command(self, task_info: DownloadTaskInfo):
        def get_video_temp_file_name():
            return f"video_{task_info.id}.m4s"

        def get_audio_temp_file_name():
            return f"audio_{task_info.id}.{task_info.audio_type}"

        def get_output_temp_file_name():
            match StreamType(task_info.stream_type):
                case StreamType.Dash:
                    match DownloadOption(task_info.download_option):
                        case DownloadOption.VideoAndAudio | DownloadOption.OnlyVideo:
                            return f"out_{task_info.id}.mp4"
                        
                        case DownloadOption.OnlyAudio:
                            return f"out_{task_info.id}.{task_info.audio_type}"
                
                case StreamType.Flv:
                    return f"out_{task_info.id}.flv"
        
        def get_full_file_name():
            match DownloadOption(task_info.download_option):
                case DownloadOption.VideoAndAudio:
                    return f"{task_info.title}.mp4"
                
                case DownloadOption.OnlyVideo:
                    return f"{task_info.title}.mp4"
                
                case DownloadOption.OnlyAudio:
                    return f"{task_info.title}.{task_info.audio_type}"
        
        def get_merge_command():
            return f'"{Config.FFmpeg.path}" -y -i "{get_video_temp_file_name()}" -i "{get_audio_temp_file_name()}" -acodec copy -vcodec copy -strict experimental {get_output_temp_file_name()}'

        def get_convent_command():
            if task_info.audio_type == "m4a" and Config.Merge.m4a_to_mp3:
                return f'"{Config.FFmpeg.path}" -y -i "{get_audio_temp_file_name()}" -c:a libmp3lame -q:a 0 "{get_output_temp_file_name()}"'
            elif task_info.audio_type == "flac":
                return f'"{Config.FFmpeg.path}" -y -i "{get_audio_temp_file_name()}" -c:a flac -q:a 0 "{get_output_temp_file_name()}"'
            else:
                return get_rename_command(get_audio_temp_file_name(), get_output_temp_file_name())

        def get_rename_command(src: str, dst: str):
            def get_sys_rename_command():
                match Config.Sys.platform:
                    case "windows":
                        return "rename"

                    case "linux" | "darwin":
                        return "mv"

            def get_escape_character():
                match Config.Sys.platform:
                    case "windows" | "darwin":
                        return ""
                    
                    case "linux":
                        return "--"

            return f'{get_sys_rename_command()} "{src}" {get_escape_character()}"{dst}"'

        command = Command()

        match DownloadOption(task_info.download_option):
            case DownloadOption.VideoAndAudio:
                command.add(get_merge_command())
                command.add(get_rename_command(get_output_temp_file_name(), get_full_file_name()))

            case DownloadOption.OnlyVideo:
                command.add(get_rename_command(get_video_temp_file_name(), get_full_file_name()))
            
            case DownloadOption.OnlyAudio:
                command.add(get_convent_command())
                command.add(get_rename_command(get_output_temp_file_name(), get_full_file_name()))
        
        return command.format()
    
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
