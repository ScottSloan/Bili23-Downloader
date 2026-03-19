class FFmpegCommand:
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.params = []

    def add_input(self, input_path: str):
        self.inputs.append(input_path)

        return self

    def add_output(self, output_path: str):
        self.outputs.append(output_path)

        return self

    def add_param(self, *args: str):
        self.params.extend(args)

        return self

    def build(self):
        command = ["ffmpeg", "-y"]

        for input_path in self.inputs:
            command.extend(["-i", input_path])

        command.extend(self.params)

        for output_path in self.outputs:
            command.append(output_path)

        return command
    
    @classmethod
    def merge_video_audio(cls, video_path: str, audio_path: str, output_path: str):
        return (
            cls()
            .add_input(video_path)
            .add_input(audio_path)
            .add_param("-acodec", "copy")
            .add_param("-vcodec", "copy")
            .add_output(output_path)
        )