"""
附加内容（弹幕 / 字幕 / 封面 / 章节 / 元数据）的编排 —— 不依赖 Qt

按 D4，这些内容**不进 aria2**：它们是几十 KB 的小文件，还要就地转成 ASS / NFO 再落盘，
交给下载器只会多一层状态机。全部走 `network/request.py` 的 `SyncNetWorkRequest`（httpx 阻塞版），
两端共用。

原先这段编排长在 `worker.py` 的 QObject 里，WebUI 用不了。按 ffmpeg 那边同样的做法
（`process.py` 纯逻辑 + `task.py` 薄壳）拆开：编排在这里，桌面侧的 QObject 外壳留在 worker.py。

**两端必须跑同一份编排。** 这里的顺序不是随意的：

- `subtitle_track_list` 要先清空 —— 暂停恢复或失败重试会重新走一遍，不清空就会把同一个
  ASS 文件重复登记，最终被嵌入多条相同的轨道
- 字幕与章节来自同一个播放器信息接口，**只请求一次**，两者共用返回结果

这些细节一旦在两端各写一遍就会悄悄分叉，而分叉的后果要到合并阶段才看得出来。
"""

from ...common.enum import DownloadType
from ...common.signal_bus import signal_bus
from ...common.translator import Translator

from ...download.task.info import TaskInfo

from .chapter import ChapterParser
from .cover import CoverParser
from .metadata import MetadataParser
from .player import PlayerInfoParser
from .subtitles import SubtitlesParser

import logging

logger = logging.getLogger(__name__)

class AdditionalRunner:
    """
    跑一遍附加内容解析

    阻塞执行，调用方自行决定放在哪个线程上：桌面侧是 `AdditionalParseWorker` 的 QThread，
    服务端侧是 `web/download/additional.py` 丢进 background 线程池
    """

    def __init__(self, task_info: TaskInfo):
        self.task_info = task_info

    def run(self):
        # 读取 Download Type 标志位，决定下载哪种类型的附加文件
        attr = self.task_info.Download.type

        # 待嵌入的字幕轨在下方逐条追加。任务暂停恢复或失败重试时会重新走一遍附加内容解析，
        # 不先清空就会把同一个 ASS 文件重复登记，最终被嵌入多条相同的轨道
        self.task_info.File.subtitle_track_list.clear()

        need_subtitle = attr & DownloadType.SUBTITLE != 0
        need_chapter = ChapterParser.is_available(self.task_info)

        if attr & DownloadType.DANMAKU != 0:
            # 下载弹幕
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_DANMAKU"))

            # ASS 弹幕要用 QFontMetrics 量文字宽度，而它需要进程里有 QGuiApplication。
            # 在这里就地导入，好让「只下 XML 弹幕」的场景完全不碰 Qt（详见 danmaku.py）
            from .danmaku import DanmakuParser

            parser = DanmakuParser(self.task_info)
            parser.parse()

        # 字幕和章节来自同一个播放器信息接口，只请求一次
        player_data = PlayerInfoParser(self.task_info).get_data() if need_subtitle or need_chapter else {}

        if need_subtitle:
            # 下载字幕
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_SUBTITLES"))

            parser = SubtitlesParser(self.task_info)
            parser.parse(player_data)

        if need_chapter:
            # 获取章节信息，生成供 FFmpeg 使用的章节文件
            self.update_status_label(Translator.TIP_MESSAGES("PARSING_CHAPTER"))

            parser = ChapterParser(self.task_info)
            parser.parse(player_data)

        if attr & DownloadType.COVER != 0:
            # 下载封面
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_COVER"))

            parser = CoverParser(self.task_info)
            parser.parse()

        if attr & DownloadType.METADATA != 0:
            # 下载元数据
            self.update_status_label(Translator.TIP_MESSAGES("SCRAPING_METADATA"))

            parser = MetadataParser(self.task_info)
            parser.parse()

        self.update_status_label("")

    def update_status_label(self, label: str):
        self.task_info.Download.status_label = label

        # 通知界面更新下载项的显示信息。signal_bus 已是纯 Python 事件，
        # 服务端进程里没有订阅者时就是一次空转
        signal_bus.download.update_downloading_item.emit(self.task_info)
