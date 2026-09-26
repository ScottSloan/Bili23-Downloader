"""
独立音频流的重封装命令。

B 站的 DASH 独立音频流是 fMP4 **分片**容器（ftyp=iso5/dash，moov 不含采样表，样本散在
moof 里），只改扩展名交付会被 foobar2000 这类严格解析器拒绝。因此交付前必须用 FFmpeg
重封装成与扩展名一致的标准容器。

这里把命令的 argv 钉死，原因是 m4a 之外的两路 —— Hi-Res 无损（flac）与杜比全景声（ec3）
—— 需要大会员账号才能取到真实流，无法用真实文件验证。断言「三种扩展名跑的是同一条命令」
是把「无法实测」压缩到只剩「FFmpeg 自身对 flac/ec3 的行为」，而那一层已在真实 m4a 流上
实测过：该命令能把 fMP4 还原成 moov 前置、带完整采样表的标准容器；对 flac/ec3 输出，
FFmpeg 会静默忽略 movflags（非 mov 系容器），所以不需要按容器分支。
"""

import pytest


@pytest.fixture
def command():
    from util.ffmpeg.command import FFmpegCommand

    return FFmpegCommand


class TestRemuxAudioCommand:
    def test_argv_is_frozen(self, command):
        argv = command.remux_audio("audio_1.m4a", "remux_1.m4a").build()

        assert argv == [
            "ffmpeg", "-y",
            "-i", "audio_1.m4a",
            "-c", "copy",
            "-movflags", "+faststart",
            "-strict", "unofficial",
            "remux_1.m4a",
        ]

    @pytest.mark.parametrize("ext", ["m4a", "flac", "ec3"])
    def test_params_do_not_depend_on_ext(self, command, ext):
        # 参数段逐字相同，只有输入输出路径随扩展名变。
        # 任何「按扩展名分支」的改动都会让这条断言失败 —— 那正是本次要去掉的形态
        baseline = command.remux_audio("in.m4a", "out.m4a").build()
        argv = command.remux_audio(f"in.{ext}", f"out.{ext}").build()

        assert argv[4:-1] == baseline[4:-1]
        assert argv[3] == f"in.{ext}"
        assert argv[-1] == f"out.{ext}"

    def test_is_a_stream_copy(self, command):
        # -c copy 是「不重编码」的保证：只有重写容器，音质与耗时都不受影响
        argv = command.remux_audio("in.m4a", "out.m4a").build()

        assert "copy" in argv
        assert "libmp3lame" not in argv
