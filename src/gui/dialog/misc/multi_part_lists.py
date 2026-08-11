from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, CheckBox

from gui.component.widget.tree_view import CheckListView
from gui.component.dialog import DialogBase

from util.parse.episode.video import VideoEpisodeParser
from util.common.enum import ToastNotificationCategory
from util.parse.parser.video import VideoParser
from util.parse.episode.tree import TreeItem, Attribute, EpisodeData
from util.common.signal_bus import signal_bus
from util.thread.async_ import AsyncTask
from util.common.config import config
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
        # 本对话框与解析界面可以同时解析，这里只登记为活跃，不清空解析界面已有的剧集数据
        with EpisodeData.parsing(clear_cache = False):
            try:
                # 解析视频 URL，获取视频信息数据
                video_parser = VideoParser()

                info_data = video_parser.parse(self.url, get_info_data = True)

                # 去除 ugc_season 字段，避免影响后续的分P解析
                if "ugc_season" in info_data["data"]:
                    del info_data["data"]["ugc_season"]

                # 解析视频分P列表
                episode_parser = VideoEpisodeParser(info_data, "USER_UPLOADS")
                node = episode_parser.parse(update_episode_list = False)

                self.success.emit(node)

            except Exception as e:
                self.error.emit(str(e))

            finally:
                # deleteLater 由 AsyncTask 统一挂在 finished 上，此处不再重复调用
                self.finished.emit()

class MultiPartListsDialog(DialogBase):
    def __init__(self, item: dict, parent = None):
        super().__init__(parent)

        self.item = item
        self.total = 0

        self.init_UI()

        self.init_multi_part_list()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Multi-part video list"), self)

        self.check_all_chk = CheckBox(self.tr("Check All"), self)
        self.count_lab = BodyLabel("", self)

        self.part_list = CheckListView(self)

        count_layout = QHBoxLayout()
        count_layout.addWidget(self.check_all_chk)
        count_layout.addSpacing(10)
        count_layout.addWidget(self.count_lab)
        count_layout.addStretch()

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(count_layout)
        self.viewLayout.addWidget(self.part_list)

        self.widget.setMinimumWidth(600)
        self.widget.setMinimumHeight(450)

        self.yesButton.setText(self.tr("Download Selected Items"))
        self.yesButton.setEnabled(False)

        self.check_all_chk.stateChanged.connect(self.on_check_all_chk_stateChanged)

    def init_multi_part_list(self):
        self.part_list.setColumnHeaders([self.tr("No."), self.tr("Title"), self.tr("Duration")], [90, 300, 100])

        worker = ParseWorker(self.item.get("url", ""))
        worker.success.connect(self.update_multi_part_list)
        # 连到 lambda 会在解析线程里就地执行，弹通知必须回到 GUI 线程，因此改用本对话框的方法
        worker.error.connect(self.on_parse_error)

        AsyncTask.run(worker)

    def on_parse_error(self, error: str):
        self.show_top_toast_message(ToastNotificationCategory.ERROR, "解析失败", error)

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
            self.yesButton.setEnabled(True)
        else:
            self.count_lab.setText(self.tr("{total_count} total").format(total_count = self.total))
            self.yesButton.setEnabled(False)

    def on_check_all_chk_stateChanged(self, state):
        if state == 2:
            self.part_list.checkAll()
        else:
            self.part_list.uncheckAll()

    def accept(self):
        # 获取选中的下载项，排除树节点
        checked_episodes_list = [entry for entry in self.part_list.getCheckedItemsData() if entry.get("attribute", 0) & Attribute.TREE_NODE_BIT == 0]

        if not checked_episodes_list:
            return

        config.current_starting_number = 1

        # 添加到下载队列
        signal_bus.download.create_task.emit(checked_episodes_list, True)

        return super().accept()