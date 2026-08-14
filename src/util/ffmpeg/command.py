from typing import List


class FFmpegCommand:
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.params = []

    def add_input(self, input_path: str, *options: str):
        # options 为该路输入的前置参数，如 -f concat，统一走此处以保证输入索引可靠
        self.inputs.append((list(options), input_path))

        return self

    def add_output(self, output_path: str):
        self.outputs.append(output_path)

        return self

    def add_param(self, *args: str):
        self.params.extend(args)

        return self

    def add_cover(self, cover_path: str, *maps: str):
        # 将封面作为附加视频流嵌入，maps 为各路流的映射关系
        self.add_input(cover_path)

        for map_param in maps:
            self.add_param("-map", map_param)

        return (
            self
            .add_param("-c:v:1", "png")
            .add_param("-disposition:v:1", "attached_pic")
            .add_param("-pix_fmt:v:1", "rgba")
        )

    def add_subtitles(self, subtitle_list: List[dict]):
        # 将 ASS 弹幕/字幕作为独立字幕轨嵌入，仅 MKV 容器支持
        #
        # 调用前必须保证主视频流与音频流已经显式 -map：只要命令中出现任意一个 -map，
        # FFmpeg 的默认流选择就会失效，此时不显式映射主流会导致输出文件里只剩字幕
        for index, entry in enumerate(subtitle_list):
            input_index = len(self.inputs)

            self.add_input(entry["file"])
            self.add_param("-map", f"{input_index}:s:0")

            if title := entry.get("title"):
                self.add_param(f"-metadata:s:s:{index}", f"title={title}")

            if language := entry.get("language"):
                self.add_param(f"-metadata:s:s:{index}", f"language={language}")

            # 每条轨都要显式给出 disposition：不指定时 FFmpeg 会自动把第一条字幕轨标记为
            # default，弹幕轨一旦落到首位就会变成打开视频即自动显示
            self.add_param(f"-disposition:s:{index}", "default" if entry.get("default") else "0")

        return self.add_param("-c:s", "copy")

    def add_chapter(self, chapter_path: str):
        # 将 ffmetadata 格式的章节文件作为额外输入写入最终文件
        # MKV 原生支持章节；MP4 由 FFmpeg 同时写入 Nero chpl 与 QuickTime 章节轨，两者命令一致
        # 此处只指定 -map_chapters，不使用 -map_metadata，否则全局元数据会被章节文件覆盖
        index = len(self.inputs)

        # ffmetadata 输入不含任何流，不会影响封面等 -map 参数的流映射
        self.add_input(chapter_path, "-f", "ffmetadata")

        return self.add_param("-map_chapters", str(index))

    def build(self):
        command = ["ffmpeg", "-y"]

        for options, input_path in self.inputs:
            command.extend([*options, "-i", input_path])

        command.extend(self.params)

        for output_path in self.outputs:
            command.append(output_path)

        return command
    
    @classmethod
    def merge_video_audio(cls, video_path: str, audio_path: str, output_path: str, cover_path: str = None, chapter_path: str = None, subtitle_list: List[dict] = None):
        command = (
            cls()
            .add_input(video_path)
            .add_input(audio_path)
            .add_param("-c:v", "copy")
            .add_param("-c:a", "copy")
        )

        if cover_path:
            # 封面为第三路输入，索引为 2
            command.add_cover(cover_path, "0:v:0", "1:a:0", "2:v:0")

        elif subtitle_list:
            # 没有封面时主流本来靠 FFmpeg 的默认选择，而字幕轨的 -map 会让默认选择失效，
            # 因此这里必须把主流一并显式映射
            command.add_param("-map", "0:v:0").add_param("-map", "1:a:0")

        # 字幕输入必须排在封面之后：add_cover 的流映射里写死了封面的输入索引
        if subtitle_list:
            command.add_subtitles(subtitle_list)

        if chapter_path:
            command.add_chapter(chapter_path)

        return command.add_output(output_path)

    @classmethod
    def merge_video_parts(cls, lists_path: str, output_path: str, cover_path: str = None, chapter_path: str = None, subtitle_list: List[dict] = None):
        command = (
            cls()
            .add_input(lists_path, "-f", "concat", "-safe", "0")
            .add_param("-c:v", "copy")
            .add_param("-c:a", "copy")
        )

        if cover_path:
            # 分片视频为第一路输入，封面为第二路输入
            # 音频用可选映射（0:a?），避免显式 -map 之后音轨被丢弃，同时兼容没有音轨的分片
            command.add_cover(cover_path, "0:v:0", "0:a?", "1:v:0")

        elif subtitle_list:
            # 同 merge_video_audio，字幕轨的 -map 会让默认流选择失效，主流必须显式映射
            command.add_param("-map", "0:v:0").add_param("-map", "0:a?")

        if subtitle_list:
            command.add_subtitles(subtitle_list)

        if chapter_path:
            command.add_chapter(chapter_path)

        return command.add_output(output_path)

    @classmethod
    def convert_m4a_to_mp3(cls, input_path: str, output_path: str):
        return (
            cls()
            .add_input(input_path)
            .add_param("-c:a", "libmp3lame")
            .add_param("-q:a", "2")
            .add_output(output_path)
        )
    
    @classmethod
    def fix_mp4_box(cls, input_path: str, output_path: str):
        return (
            cls()
            .add_input(input_path)
            .add_param("-c", "copy")
            .add_param("-movflags", "+faststart")
            .add_output(output_path)
        )