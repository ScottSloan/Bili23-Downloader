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
