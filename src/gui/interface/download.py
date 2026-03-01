from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout

from qfluentwidgets import SubtitleLabel, Pivot

from gui.component.download.top_widget import TopStackedWidget
from gui.component.download.list_view import DownloadListView
from gui.component.widget import PivotItem

from util.download.task.query_worker import QueryWorker
from util.download.task.info import TaskInfo
from util.thread import AsyncTask

class DownloadInterface(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setObjectName("DownloadInterface")

        self.init_UI()

        self.get_tasks()

    def init_UI(self):
        self.pivot = Pivot(self)
        self.list_stacked_widget = QStackedWidget(self)
        self.list_stacked_widget.setContentsMargins(0, 10, 0, 5)

        self.top_stacked_widget = TopStackedWidget(self)

        self.downloading_list_view = DownloadListView(self)
        self.downloading_list_view.setEmptyTextTip(self.tr("No downloads in progress"))

        self.completed_list_view = DownloadListView(self)
        self.completed_list_view.setEmptyTextTip(self.tr("No completed downloads"))

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.pivot)
        top_layout.addStretch()
        top_layout.addWidget(self.top_stacked_widget)

        self.addSubInterface(self.downloading_list_view, "downloading", self.tr("Downloading"), 0)
        self.addSubInterface(self.completed_list_view, "completed", self.tr("Completed"), 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.list_stacked_widget)

        self.pivot.setCurrentItem("downloading")

    def addSubInterface(self, widget: SubtitleLabel, objectName: str, text: str, index):
        def onClick():
            self.list_stacked_widget.setCurrentWidget(widget)
            self.top_stacked_widget.setCurrentIndex(index)

        widget.setObjectName(objectName)
        self.list_stacked_widget.addWidget(widget)

        item = PivotItem(text = text, parent = self.pivot)
        item.setMaximumWidth(150)
        item.setFontSize(15)

        item = self.pivot.insertWidget(-1, objectName, item, onClick)

    def get_tasks(self):
        # 从数据库中查询下载任务，并添加到列表中
        worker = QueryWorker()
        worker.success.connect(self.on_query_success)
        worker.error.connect(self.on_query_error)

        AsyncTask.run(worker)
    
    def on_query_success(self, downloading_tasks: list[TaskInfo], completed_tasks: list[TaskInfo]):
        self.downloading_list_view.add_task(downloading_tasks)
        self.completed_list_view.add_task(completed_tasks)

    def on_query_error(self, error_message: str):
        print(f"查询下载任务失败: {error_message}")
        
