"""
独立音频流的重封装命令。

B 站的 DASH 独立音频流是 fMP4 **分片**容器（ftyp=iso5/dash，moov 不含采样表，样本散在
moof 里），只改扩展名交付会被 foobar2000 这类严格解析器拒绝。因此交付前必须用 FFmpeg
重封装成与扩展名一致的标准容器。

这里把命令的 argv 钉死，原因是 m4a 之外的两路 —— Hi-Res 无损（flac）与杜比全景声（ec3）
—— 需要大会员账号才能取到真实流，无法用真实文件验证。断言「三种扩展名除了 -f 之外跑的是
同一条命令」是把「无法实测」压缩到只剩「FFmpeg 自身对 flac/ec3 的行为」，而那一层已在真实
m4a 流上实测过：该命令能把 fMP4 还原成 moov 前置、带完整采样表的标准容器；对 flac/ec3 输出，
FFmpeg 会静默忽略 movflags（非 mov 系容器），所以不需要按容器分支。

唯一随扩展名变的是 -f。它不能省：附带的精简版 FFmpeg 没有 ipod/eac3 封装器，按扩展名猜
格式会直接失败（#351、#476），而开发机上装的完整版 FFmpeg 永远复现不出来，只能靠这里钉住。
"""

import pytest


@pytest.fixture
def command():
    from util.ffmpeg.command import FFmpegCommand

    return FFmpegCommand


def strip_format(argv):
    # 去掉 -f 及其取值，剩下的就是与扩展名无关的公共部分
    index = argv.index("-f")

    return argv[:index] + argv[index + 2:]


class TestRemuxAudioCommand:
    def test_argv_is_frozen(self, command):
        argv = command.remux_audio("audio_1.m4a", "remux_1.m4a").build()

        assert argv == [
            "ffmpeg", "-y",
            "-i", "audio_1.m4a",
            "-c", "copy",
            "-movflags", "+faststart",
            "-strict", "unofficial",
            "-f", "mp4",
            "remux_1.m4a",
        ]

    @pytest.mark.parametrize("ext, muxer", [
        # m4a 刻意用 mp4 而不是 ipod：已经发出去的附带版 FFmpeg 没有 ipod，
        # 而两者的输出只差 ftyp 的 major brand
        ("m4a", "mp4"),
        ("flac", "flac"),
        ("ec3", "eac3"),
    ])
    def test_muxer_is_explicit(self, command, ext, muxer):
        argv = command.remux_audio(f"in.{ext}", f"out.{ext}").build()

        # -f 是输出选项，必须紧贴在输出路径之前，放到 -i 前面就成了输入格式
        assert argv[-3:] == ["-f", muxer, f"out.{ext}"]

    @pytest.mark.parametrize("ext", ["m4a", "flac", "ec3"])
    def test_params_do_not_depend_on_ext(self, command, ext):
        # 除 -f 外参数段逐字相同，只有输入输出路径随扩展名变
        baseline = strip_format(command.remux_audio("in.m4a", "out.m4a").build())
        argv = strip_format(command.remux_audio(f"in.{ext}", f"out.{ext}").build())

        assert argv[4:-1] == baseline[4:-1]
        assert argv[3] == f"in.{ext}"
        assert argv[-1] == f"out.{ext}"

    def test_every_dash_audio_ext_has_muxer(self):
        # 新增一种独立音频流扩展名却忘了登记封装器，就会退回按扩展名猜格式的老路
        from util.download.downloader.merger import DASH_AUDIO_STREAM_EXTS
        from util.ffmpeg.command import REMUX_AUDIO_MUXERS

        assert set(DASH_AUDIO_STREAM_EXTS) <= set(REMUX_AUDIO_MUXERS)

    def test_is_a_stream_copy(self, command):
        # -c copy 是「不重编码」的保证：只有重写容器，音质与耗时都不受影响
        argv = command.remux_audio("in.m4a", "out.m4a").build()

        assert "copy" in argv
        assert "libmp3lame" not in argv


def option_values(argv, option):
    # 取出某个选项的全部取值，用于断言 -map 这类可重复出现的参数
    return [argv[index + 1] for index, arg in enumerate(argv) if arg == option]


class TestMergeCoverCommand:
    """
    封面在两种容器里走的是两套机制，不能共用一条命令（#493）。

    MP4 认 attached_pic 视频流；matroska 封装器却会丢掉这个 disposition，同样的写法到了 MKV
    里就成了一条普通的 PNG 视频轨，播放器会多出一条视频轨、资源管理器也不显示封面。MKV 必须
    改用 Matroska 附件，而附件按 cover.<ext> 命名才会被识别为封面。
    """

    def test_mp4_cover_is_attached_pic_stream(self, command):
        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mp4", cover_path = "c.jpg").build()

        assert argv[argv.index("c.jpg") - 1] == "-i"
        assert option_values(argv, "-map") == ["0:v:0", "1:a:0", "2:v:0"]
        assert option_values(argv, "-disposition:v:1") == ["attached_pic"]
        assert "-attach" not in argv

    def test_mkv_cover_is_attachment(self, command):
        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mkv", cover_path = "c.jpg").build()

        # 附件不是输入，不能出现在 -i 之后，也不能占用视频流的位置
        assert option_values(argv, "-i") == ["v.m4s", "a.m4s"]
        assert option_values(argv, "-attach") == ["c.jpg"]
        assert option_values(argv, "-map") == ["0:v:0", "1:a:0"]
        assert option_values(argv, "-metadata:s:t:0") == ["mimetype=image/jpeg", "filename=cover.jpg"]
        assert "-disposition:v:1" not in argv
        assert "png" not in argv

    @pytest.mark.parametrize("ext, mimetype", [
        ("jpg", "image/jpeg"),
        ("png", "image/png"),
        ("webp", "image/webp"),
        ("avif", "image/avif"),
    ])
    def test_every_cover_type_has_mimetype(self, command, ext, mimetype):
        # Matroska 附件缺 mimetype 时 FFmpeg 会直接报错退出
        from util.common.enum import CoverType
        from util.ffmpeg.command import COVER_ATTACHMENT_MIMETYPES

        assert {cover_type.value for cover_type in CoverType} <= set(COVER_ATTACHMENT_MIMETYPES)

        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mkv", cover_path = f"c.{ext}").build()

        assert option_values(argv, "-metadata:s:t:0") == [f"mimetype={mimetype}", f"filename=cover.{ext}"]

    def test_mkv_cover_with_subtitles(self, command):
        subtitle_list = [{"file": "s.ass", "kind": "subtitle", "default": True}]

        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mkv", cover_path = "c.jpg", subtitle_list = subtitle_list).build()

        # 封面不再占输入索引，字幕成了第三路输入
        assert option_values(argv, "-i") == ["v.m4s", "a.m4s", "s.ass"]
        assert option_values(argv, "-map") == ["0:v:0", "1:a:0", "2:s:0"]

    def test_mp4_cover_index_follows_inputs(self, command):
        # 封面的输入索引由 add_cover 现取，分片合并时封面是第二路输入
        argv = command.merge_video_parts("lists.txt", "out.mp4", cover_path = "c.jpg").build()

        assert option_values(argv, "-map") == ["0:v:0", "0:a?", "1:v:0"]

    def test_parts_mkv_cover_is_attachment(self, command):
        argv = command.merge_video_parts("lists.txt", "out.mkv", cover_path = "c.png").build()

        assert option_values(argv, "-attach") == ["c.png"]
        assert option_values(argv, "-map") == ["0:v:0", "0:a?"]


class TestMatroskaHevcTag:
    """
    杜比视界的 HEVC 流在 MP4 里标签是 dvh1，matroska 封装器不认，流拷贝进 MKV 会直接合并失败（#499）。
    换成 hvc1 才能通过校验；但这个标签只能给 HEVC，H.264 带上它同样会让合并失败。
    """

    def test_mkv_hevc_is_retagged(self, command):
        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mkv", hevc = True).build()

        assert option_values(argv, "-tag:v:0") == ["hvc1"]

    @pytest.mark.parametrize("output, hevc", [
        # MP4 必须保留 dvh1，否则播放器不再按杜比视界识别
        ("out.mp4", True),
        # H.264 带上 hvc1 会报 "Tag hvc1 incompatible with output codec id"
        ("out.mkv", False),
        ("out.mp4", False),
    ])
    def test_tag_is_untouched_otherwise(self, command, output, hevc):
        argv = command.merge_video_audio("v.m4s", "a.m4s", output, hevc = hevc).build()

        assert "-tag:v:0" not in argv

    def test_mkv_hevc_with_cover(self, command):
        # 附件是 t 类型的流，不影响 v:0 指向主视频
        argv = command.merge_video_audio("v.m4s", "a.m4s", "out.mkv", cover_path = "c.jpg", hevc = True).build()

        assert option_values(argv, "-tag:v:0") == ["hvc1"]
        assert option_values(argv, "-attach") == ["c.jpg"]
