from PySide6.QtCore import QSize, QModelIndex, Qt, QRect, QEvent, QObject
from PySide6.QtWidgets import QStyleOptionViewItem
from PySide6.QtGui import QPainter, QMouseEvent

from qfluentwidgets import FluentIcon

from gui.component.view_model import CoverQueryDelegateBase

from util.common import ExtendedFluentIcon, Translator, Directory
from util.common.enum import DownloadStatus
from util.format import Units, Time

from util.download import TaskInfo

from pathlib import Path

class DownloadItemDelegate(CoverQueryDelegateBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()
        self.uiData = UIData(self)

        self.ActionButtonHoveredRow = -1
        self.DeleteButtonHoveredRow = -1

    def sizeHint(self, option, index):
        return QSize(0, 100)

    def editorEvent(self, event: QEvent, model, option, index: QModelIndex):
        view = self.parent()

        if event.type() == QEvent.Type.MouseMove:
            self._buttonHoverEvent(option, index, event)
            view.update(index)

        if event.type() == QEvent.Type.Leave:
            self.hoverRow = -1
            view.update()

        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)

        return super().editorEvent(event, model, option, index)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # 获取任务信息
        task_info: TaskInfo = index.data(Qt.ItemDataRole.UserRole)

        # 左侧封面、标题和信息
        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, option, index, task_info.Basic.cover_id, task_info.Episode.cover)

        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, task_info.Basic.show_title)

        infoRect = self.uiRect.getInfoRect(titleRect, option, completed = self.isTaskCompleted(task_info))
        self._drawDescriptionText(painter, infoRect, self.uiData.getInfoText(task_info))

        sizeRect = self.uiRect.getSizeRect(infoRect)
        self._drawDescriptionText(painter, sizeRect, self.uiData.getSizeText(task_info))


        # 右侧进度条、状态
        progressBarRect = self.uiRect.getProgressBarRect(titleRect, option)
        self._drawProgressBar(painter, progressBarRect, task_info.Download.progress, error = self.isTaskFailed(task_info), paused = self.isTaskPaused(task_info))

        statusRect = self.uiRect.getStatusRect(progressBarRect, infoRect, option)
        self._drawDescriptionText(painter, statusRect, self.uiData.getStatusText(task_info), error = self.isTaskFailed(task_info))


        # 右侧控制和删除按钮
        actionButtonRect = self.uiRect.getActionButtonRect(option)
        self._drawPrimaryButton(painter, actionButtonRect, self.uiData.getButtonIcon(task_info), self.ActionButtonHoveredRow == index.row())

        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)
        self._drawButton(painter, deleteButtonRect, FluentIcon.DELETE, self.DeleteButtonHoveredRow == index.row())
    
    def _buttonHoverEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event: QMouseEvent):
        pos = event.pos()

        actionButtonRect = self.uiRect.getActionButtonRect(option)
        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)

        if actionButtonRect.contains(pos):
            self.ActionButtonHoveredRow = index.row()
        else:
            self.ActionButtonHoveredRow = -1

        if deleteButtonRect.contains(pos):
            self.DeleteButtonHoveredRow = index.row()
        else:
            self.DeleteButtonHoveredRow = -1

    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event: QMouseEvent):
        pos = event.pos()

        if event.button() == Qt.MouseButton.RightButton:
            # 右键点击，弹出上下文菜单
            self.contextMenuRequested.emit(index, event.globalPos())

            return True

        actionButtonRect = self.uiRect.getActionButtonRect(option)
        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)

        if actionButtonRect.contains(pos):
            task_info: TaskInfo = index.data(Qt.ItemDataRole.UserRole)

            match task_info.Download.status:
                case DownloadStatus.COMPLETED:
                    self.openFileLocation(task_info)

                case _:
                    index.model().togglePauseResume(task_info)

            index.model().dataChanged.emit(index, index)

            return True

        if deleteButtonRect.contains(pos):
            index.model().cancelDownload(index.data(Qt.ItemDataRole.UserRole))

            return True

        return False

    def openFileLocation(self, task_info: TaskInfo):
        directory = Path(task_info.File.download_path, task_info.File.folder)

        Directory.open_files_in_explorer(str(directory), task_info.File.relative_files)

    def isTaskCompleted(self, task_info: TaskInfo):
        return task_info.Download.status == DownloadStatus.COMPLETED
    
    def isTaskFailed(self, task_info: TaskInfo):
        return task_info.Download.status in [DownloadStatus.FAILED, DownloadStatus.FFMPEG_FAILED]
    
    def isTaskPaused(self, task_info: TaskInfo):
        return task_info.Download.status == DownloadStatus.PAUSED

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = self.margin * 2
        self.buttonSize = 32

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()

        return QRect(self.margin, top, 144, 80)

    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 5

        width = option.rect.width() - 450

        return QRect(left, top, width, 20)
    
    def getInfoRect(self, titleRect: QRect, option: QStyleOptionViewItem, completed = False):
        left = titleRect.left()
        top = option.rect.bottom() - titleRect.height() - self.margin - 5

        if completed:
            width = 175
        else:
            width = 125
        
        return QRect(left, top, width, 20)
    
    def getSizeRect(self, infoRect: QRect):
        left = infoRect.right() + self.margin

        top = infoRect.top()

        return QRect(left, top, 150, 20)

    def getProgressBarRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        left = option.rect.width() - self.margin - self.buttonSize * 2 - self.spacer * 3 - 200
        top = (option.rect.height() - 16) / 2 + option.rect.top()  #titleRect.top() + self.margin

        return QRect(left, top, 200, 16)
    
    def getStatusRect(self, progressBarRect: QRect, infoRect: QRect, option: QStyleOptionViewItem):
        left = progressBarRect.left()
        top = infoRect.top()

        return QRect(left, top, 200, 20)

    def getActionButtonRect(self, option: QStyleOptionViewItem):
        left = option.rect.width() - self.buttonSize * 2 - self.spacer * 2
        top = (option.rect.height() - self.buttonSize) / 2 + option.rect.top()

        return QRect(left, top, self.buttonSize, self.buttonSize)
    
    def getDeleteButtonRect(self, option: QStyleOptionViewItem):
        left = option.rect.width() - self.buttonSize - self.spacer * 2 + self.margin
        top = (option.rect.height() - self.buttonSize) / 2 + option.rect.top()

        return QRect(left, top, self.buttonSize, self.buttonSize)

class UIData(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

    def getInfoText(self, task_info: TaskInfo):
        if task_info.Download.status == DownloadStatus.COMPLETED:
            return Time.format_timestamp(task_info.Basic.completed_time)
        else:
            return task_info.Download.info_label

    def getStatusText(self, task_info: TaskInfo):
        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                return Translator.TIP_MESSAGES("QUEUED")
            
            case DownloadStatus.PARSING:
                return Translator.TIP_MESSAGES("PARSING")
            
            case DownloadStatus.DOWNLOADING:
                return self.getSpeedText(task_info)
            
            case DownloadStatus.PAUSED:
                return Translator.TIP_MESSAGES("PAUSED")
            
            case DownloadStatus.FFMPEG_QUEUED:
                return Translator.TIP_MESSAGES("FFMPEG_QUEUED")
            
            case DownloadStatus.MERGING:
                return Translator.TIP_MESSAGES("MERGING")
            
            case DownloadStatus.ADDITIONAL_PROCESSING:
                return task_info.Download.status_label
            
            case DownloadStatus.CONVERTING:
                return Translator.TIP_MESSAGES("CONVERTING")
            
            case DownloadStatus.COMPLETED:
                return Translator.TIP_MESSAGES("COMPLETED")
            
            case DownloadStatus.FAILED:
                return Translator.ERROR_MESSAGES("DOWNLOAD_FAILED")
            
            case DownloadStatus.FFMPEG_FAILED:
                return Translator.ERROR_MESSAGES("FFMPEG_PROCESSING_FAILED")
            
    def getSpeedText(self, task_info: TaskInfo):
        return Units.format_speed(task_info.Download.speed)
    
    def getSizeText(self, task_info: TaskInfo):
        if task_info.Download.total_size > 0:

            if task_info.Download.status in [DownloadStatus.COMPLETED, DownloadStatus.FFMPEG_QUEUED, DownloadStatus.MERGING, DownloadStatus.CONVERTING, DownloadStatus.FFMPEG_FAILED]:
                return Units.format_file_size(task_info.Download.total_size)
            else:
                return f"{Units.format_file_size(task_info.Download.downloaded_size)} / {Units.format_file_size(task_info.Download.total_size)}"
            
        else:
            return ""
        
    def getButtonIcon(self, task_info: TaskInfo):
        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                return FluentIcon.FOLDER
            
            case DownloadStatus.QUEUED | DownloadStatus.PAUSED | DownloadStatus.FFMPEG_QUEUED:
                return FluentIcon.PLAY
            
            case DownloadStatus.FAILED | DownloadStatus.FFMPEG_FAILED:
                return ExtendedFluentIcon.RETRY
            
            case _:
                return FluentIcon.PAUSE
            