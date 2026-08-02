from PySide6.QtCore import QObject, Signal, Slot

from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.widget import CheckListView
from gui.component.dialog import DialogBase

from util.parse.episode.video import VideoEpisodeParser
from util.common.enum import ToastNotificationCategory
from util.parse.parser.video import VideoParser
from util.parse.episode.tree import TreeItem
from util.thread.async_ import AsyncTask
from util.format.units import Units

class ParseWorker(QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str):
        super().__init__()

        self.url = url

    @Slot()
    def run(self):
        try:
            # 解析视频 URL，获取视频信息数据
            video_parser = VideoParser()

            info_data = video_parser.parse(self.url, get_info_data = True)

            # 解析视频分P列表
            episode_parser = VideoEpisodeParser(info_data, "USER_UPLOADS")
            node = episode_parser.parse(update_episode_list = False)

            self.success.emit(node)

        except Exception as e:
            self.error.emit(str(e))
            
        finally:
            self.finished.emit()

            self.deleteLater()

class MultiPartListsDialog(DialogBase):
    def __init__(self, item: dict, parent = None):
        super().__init__(parent)

        self.item = item
        self.total = 0

        self.init_UI()

        self.init_multi_part_list()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Multi-part video list"), self)

        self.count_lab = BodyLabel("", self)

        self.part_list = CheckListView(self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.count_lab)
        self.viewLayout.addWidget(self.part_list)

        self.widget.setMinimumWidth(600)
        self.widget.setMinimumHeight(450)

        self.yesButton.setText(self.tr("Download Selected Items"))

    def init_multi_part_list(self):
        self.part_list.setColumnHeaders([self.tr("No."), self.tr("Title"), self.tr("Duration")], [90, 300, 100])

        worker = ParseWorker(self.item.get("url", ""))
        worker.success.connect(self.update_multi_part_list)
        worker.error.connect(lambda e: self.show_top_toast_message(ToastNotificationCategory.ERROR, "解析失败", e))

        AsyncTask.run(worker)

    def update_multi_part_list(self, node: TreeItem):
        for index, child in enumerate(node.children):
            entry = child.to_dict()

            self.part_list.appendCheckableRow(str(index + 1), entry["title"], Units.format_duration(entry["duration"]), data = entry)

        self.total = len(node.children)

        self.update_count_label()

        self.part_list.data_model.itemChanged.connect(self.update_count_label)

    def update_count_label(self):
        selected_count = self.part_list.getCheckedItemsCount()

        if selected_count > 0:
            self.count_lab.setText(self.tr("{selected_count} selected, {total_count} total").format(selected_count = selected_count, total_count = self.total))
        else:
            self.count_lab.setText(self.tr("{total_count} total").format(total_count = self.total))
