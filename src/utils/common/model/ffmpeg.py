from utils.config import Config

class FFmpegCommand:
    def __init__(self, input_files: list[str], output: str):
        self.input_files = input_files
        self.output = output

    def merge(self):
        params = ["-acodec", "copy", "-vcodec", "copy", "-strict", "experimental"]

        return self.construct(params)
    
    def convert_audio(self, acodec: str):
        params = ["-c:a", acodec, "-q:a", "0"]

        return self.construct(params)

    def construct(self, params: list[str]):
        command = [f'"{Config.Merge.ffmpeg_path}"', "-y"]

        for input_file in self.input_files:
            command.extend(["-i", input_file])

        command.extend(params)
        command.append(self.output)

        return " ".join(command)