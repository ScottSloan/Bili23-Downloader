from PySide6.QtCore import QSize, QModelIndex, Qt, QRect, QEvent, QObject
from PySide6.QtWidgets import QStyleOptionViewItem
from PySide6.QtGui import QPainter, QMouseEvent, QColor

from qfluentwidgets import FluentIcon, isDarkTheme

from gui.component.view_model import CoverQueryDelegateBase

from util.common.enum import DownloadStatus, DownloadType, ToastNotificationCategory
from util.common.data.media_info import reversed_video_quality_map, reversed_audio_quality_map, video_codec_str_map
from util.common.icon import ExtendedFluentIcon
from util.common.io.directory import Directory
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.download.task.info import TaskInfo
from util.format.units import Units
from util.format.time import Time
from util.parse.episode.tree import Attribute

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_media_type_key(task_info: TaskInfo):
    """
    任务的媒体类型，取值为 MEDIA_TYPE_BADGE 的 key，判断不出时返回空串

    封面角标与列表的类型筛选共用这一份判断：两边各写一套的话，迟早会出现
    角标写着「音频」、按音频筛选却筛不出来的情况
    """
    attribute = task_info.Episode.attribute
    download_type = task_info.Download.type

    # 仅下载音频时，产物就是音频文件，无论来源是投稿、番剧还是课程，都直接标「音频」
    audio_only = download_type & DownloadType.AUDIO and not download_type & DownloadType.VIDEO

    # 先判断更具体的类型：音频、课程、剧集条目也可能同时带着其他通用位
    if audio_only or attribute & Attribute.AUDIO_BIT:
        return "AUDIO"
    elif attribute & (Attribute.CHEESE_BIT | Attribute.LESSON_BIT):
        return "COURSE"
    elif attribute & Attribute.BANGUMI_BIT:
        return "BANGUMI"
    elif attribute & Attribute.INTERACTIVE_BIT:
        return "INTERACTIVE"
    elif attribute & Attribute.VIDEO_BIT:
        return "VIDEO"

    return ""

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

        failed = self.isTaskFailed(task_info)

        # 左侧封面，左上角标媒体类型，右下角标时长
        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, option, index, task_info.Basic.cover_id, task_info.Episode.cover)

        self._drawCoverBadge(painter, coverRect, self.uiData.getMediaTypeText(task_info), Qt.Corner.TopLeftCorner)
        self._drawCoverBadge(painter, coverRect, self.uiData.getDurationText(task_info), Qt.Corner.BottomRightCorner)

        # 右侧状态区：中间一行是进度条与百分比，底部一行是大小、速度、剩余时间等状态信息。
        # 会随下载跳动的数字全部收在这一块里，左侧的标题与标签在下载过程中保持静止
        statusAreaRect = self.uiRect.getStatusAreaRect(option)

        if not self.isTaskCompleted(task_info):
            progressBarRect = self.uiRect.getProgressBarRect(statusAreaRect, option)
            self._drawProgressBar(painter, progressBarRect, task_info.Download.progress, error = failed, paused = self.isTaskPaused(task_info))

            percentRect = self.uiRect.getPercentRect(progressBarRect)
            self._drawSecondaryText(painter, percentRect, self.uiData.getPercentText(task_info), alignment = Qt.AlignmentFlag.AlignRight)

        statusRect = self.uiRect.getStatusRect(statusAreaRect, option)
        self._drawSecondaryText(painter, statusRect, self.uiData.getStatusText(task_info), error = failed)

        # 左侧标题与媒体信息标签
        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, task_info.Basic.show_title)

        tagRect = self.uiRect.getTagRect(titleRect, statusAreaRect, statusRect)
        self._drawTags(painter, tagRect, self.uiData.getTagList(task_info) + self.uiData.getAdditionalTagList(task_info))

        # 右侧控制和删除按钮
        actionButtonRect = self.uiRect.getActionButtonRect(option)
        self._drawPrimaryButton(painter, actionButtonRect, self.uiData.getButtonIcon(task_info), self.ActionButtonHoveredRow == index.row())

        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)
        self._drawButton(painter, deleteButtonRect, FluentIcon.DELETE, self.DeleteButtonHoveredRow == index.row())

    def _drawSecondaryText(self, painter: QPainter, rect: QRect, text: str, error = False, alignment = Qt.AlignmentFlag.AlignLeft):
        if not text:
            return

        if error:
            textColor = QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)
        else:
            textColor = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self._drawTextBase(painter, rect, text, textColor, self.uiRect.secondaryFontSize, alignment | Qt.AlignmentFlag.AlignVCenter)

    def _drawCoverBadge(self, painter: QPainter, coverRect: QRect, text: str, corner: Qt.Corner):
        if not text:
            return

        fontSize = self.uiRect.badgeFontSize
        rect = self.uiRect.getCoverBadgeRect(coverRect, self._getTextWidth(text, fontSize), corner)

        # 角标压在封面上，封面明暗不定，固定用半透明黑底白字，与主题无关
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawRoundedRect(rect, 4, 4)

        self._drawTextBase(painter, rect, text, QColor(255, 255, 255), fontSize, Qt.AlignmentFlag.AlignCenter)

    def _drawTags(self, painter: QPainter, rect: QRect, tags: list[str]):
        if isDarkTheme():
            textColor = QColor(206, 206, 206)
            backgroundColor = QColor(255, 255, 255, 18)
        else:
            textColor = QColor(96, 96, 96)
            backgroundColor = QColor(0, 0, 0, 12)

        fontSize = self.uiRect.tagFontSize
        padding = self.uiRect.tagPadding
        spacing = self.uiRect.tagSpacing

        left = rect.left()

        # 宽度不够时从后往前整枚丢弃，不画被截断的半个标签
        for tag in tags:
            width = self._getTextWidth(tag, fontSize) + padding * 2

            if left + width > rect.right():
                return

            tagRect = QRect(left, rect.top(), width, rect.height())

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(backgroundColor)
            painter.drawRoundedRect(tagRect, 4, 4)

            self._drawTextBase(painter, tagRect, tag, textColor, fontSize, Qt.AlignmentFlag.AlignCenter)

            left += width + spacing

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

        # 检查 relative_files 是否存在，如果不存在则弹出错误提示
        existing_files = [file for file in task_info.File.relative_files if Path(directory, file).exists()]

        if not existing_files:
            # 记录第一个文件位置
            if task_info.File.relative_files:
                _path = Path(directory, task_info.File.relative_files[0])
            else:
                _path = directory

            logger.error("任务 %s 的下载文件不存在，无法打开文件位置： %s", task_info.Basic.show_title, _path)

            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                Translator.ERROR_MESSAGES("FILE_NOT_FOUND_TITLE"),
                "{msg}\n\n{path}".format(
                    msg = Translator.ERROR_MESSAGES("FILE_NOT_FOUND_DETAIL"),
                    path = str(_path)
                )
                
            )

        else:
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

        # 文字只分两级：标题 14，其余说明文字与标签 12，封面角标空间有限再小一号
        self.secondaryFontSize = 12
        self.tagFontSize = 12
        self.badgeFontSize = 11

        self.lineHeight = 20

        self.tagPadding = 7
        self.tagSpacing = 6

        self.badgeHeight = 18
        self.badgePadding = 5
        self.badgeInset = 4

        # 右侧状态区的宽度要放得下「1023.9 MB / 1023.9 MB · 10.0 MB/s · 剩余 01:03:21」
        self.statusAreaWidth = 280
        self.percentWidth = 40

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()

        return QRect(self.margin, top, 144, 80)

    def getCoverBadgeRect(self, coverRect: QRect, textWidth: int, corner: Qt.Corner):
        width = textWidth + self.badgePadding * 2

        if corner == Qt.Corner.TopLeftCorner:
            left = coverRect.left() + self.badgeInset
            top = coverRect.top() + self.badgeInset
        else:
            left = coverRect.right() - self.badgeInset - width + 1
            top = coverRect.bottom() - self.badgeInset - self.badgeHeight + 1

        return QRect(left, top, width, self.badgeHeight)

    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 5

        # 标题所在的第一行右侧没有其他元素，一直延伸到按钮前
        width = self.getActionButtonRect(option).left() - self.spacer - left

        return QRect(left, top, width, 22)

    def getStatusAreaRect(self, option: QStyleOptionViewItem):
        left = self.getActionButtonRect(option).left() - self.spacer - self.statusAreaWidth

        return QRect(left, option.rect.top(), self.statusAreaWidth, option.rect.height())

    def getProgressBarRect(self, statusAreaRect: QRect, option: QStyleOptionViewItem):
        top = option.rect.top() + (option.rect.height() - 16) // 2
        width = statusAreaRect.width() - self.percentWidth - self.margin

        return QRect(statusAreaRect.left(), top, width, 16)

    def getPercentRect(self, progressBarRect: QRect):
        left = progressBarRect.right() + self.margin
        top = progressBarRect.center().y() - self.lineHeight // 2

        return QRect(left, top, self.percentWidth, self.lineHeight)

    def getStatusRect(self, statusAreaRect: QRect, option: QStyleOptionViewItem):
        # 与封面底边留出和标题同样的 5px 内缩，使上下两行相对封面对称
        top = option.rect.top() + self.margin + 80 - 5 - self.lineHeight

        return QRect(statusAreaRect.left(), top, statusAreaRect.width(), self.lineHeight)

    def getTagRect(self, titleRect: QRect, statusAreaRect: QRect, statusRect: QRect):
        left = titleRect.left()
        width = statusAreaRect.left() - self.spacer - left

        return QRect(left, statusRect.top(), width, self.lineHeight)

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

    def getMediaTypeText(self, task_info: TaskInfo):
        key = get_media_type_key(task_info)

        if not key:
            return ""

        return Translator.MEDIA_TYPE_BADGE(key)

    def getDurationText(self, task_info: TaskInfo):
        if task_info.Episode.duration > 0:
            return Units.format_duration(task_info.Episode.duration)

        return ""

    def getPercentText(self, task_info: TaskInfo):
        # FFmpeg 要吐出第一条进度才有百分比可显示，之前（以及 copy 合并这类瞬间完成的场景）
        # 不显示数字，免得挂着一个始终停在 0% 的数字
        if task_info.Download.status in [DownloadStatus.FFMPEG_QUEUED, DownloadStatus.MERGING, DownloadStatus.CONVERTING] and task_info.Download.progress == 0:
            return ""

        return f"{task_info.Download.progress}%"

    def getStatusText(self, task_info: TaskInfo):
        # 解析中与失败只给一句状态，其余状态都以文件大小开头，后面接与该状态相关的信息，用「·」连接
        match task_info.Download.status:
            case DownloadStatus.PARSING:
                return Translator.TIP_MESSAGES("PARSING")

            case DownloadStatus.FAILED:
                # 等待自动重试期间状态仍是 FAILED，倒计时文案挂在 status_label 上，
                # 这样并发调度器（只认 QUEUED）完全不受影响，不必新增一个状态枚举
                return task_info.Download.status_label or Translator.ERROR_MESSAGES("DOWNLOAD_FAILED")

            case DownloadStatus.FFMPEG_FAILED:
                return Translator.ERROR_MESSAGES("FFMPEG_PROCESSING_FAILED")

        parts = [self.getSizeText(task_info)]

        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                parts.append(Translator.TIP_MESSAGES("QUEUED"))

            case DownloadStatus.DOWNLOADING:
                parts.append(Units.format_speed(task_info.Download.speed))
                parts.append(self.getRemainingTimeText(task_info))

            case DownloadStatus.PAUSED:
                parts.append(Translator.TIP_MESSAGES("PAUSED"))

            case DownloadStatus.FFMPEG_QUEUED:
                parts.append(Translator.TIP_MESSAGES("FFMPEG_QUEUED"))

            case DownloadStatus.MERGING:
                parts.append(Translator.TIP_MESSAGES("MERGING"))

            case DownloadStatus.ADDITIONAL_PROCESSING:
                parts.append(task_info.Download.status_label)

            case DownloadStatus.CONVERTING:
                parts.append(Translator.TIP_MESSAGES("CONVERTING"))

            case DownloadStatus.COMPLETED:
                parts.append(self.getCompletedTimeText(task_info))

        return " · ".join(part for part in parts if part)

    def getRemainingTimeText(self, task_info: TaskInfo):
        if task_info.Download.eta > 0:
            return Translator.TIP_MESSAGES("REMAINING_TIME").format(time = Units.format_duration(task_info.Download.eta))

        return ""

    def getCompletedTimeText(self, task_info: TaskInfo):
        if task_info.Basic.completed_time:
            return Translator.TIP_MESSAGES("COMPLETED_AT").format(time = Time.format_timestamp(task_info.Basic.completed_time, "%Y-%m-%d %H:%M"))

        return Translator.TIP_MESSAGES("COMPLETED")

    def getSizeText(self, task_info: TaskInfo):
        if task_info.Download.total_size > 0:

            if task_info.Download.status in [DownloadStatus.COMPLETED, DownloadStatus.FFMPEG_QUEUED, DownloadStatus.MERGING, DownloadStatus.CONVERTING, DownloadStatus.FFMPEG_FAILED]:
                return Units.format_file_size(task_info.Download.total_size)
            else:
                return f"{Units.format_file_size(task_info.Download.downloaded_size)} / {Units.format_file_size(task_info.Download.total_size)}"

        else:
            return ""

    def getTagList(self, task_info: TaskInfo):
        # 画质、编码、音质一律按 id 现查译文，不用 Episode 上存的文字：那份是建任务时按当时的界面语言
        # 写进 task.db 的，切换语言后会一直停留在旧语言。查不到（含 auto 这类尚未确定的占位值）就不画
        tags = []

        download_type = task_info.Download.type

        if download_type & DownloadType.VIDEO:
            video_quality = reversed_video_quality_map.get(task_info.Download.video_quality_id)

            if video_quality and video_quality != "auto":
                tags.append(Translator.VIDEO_QUALITY(video_quality))

            if video_codec := video_codec_str_map.get(task_info.Download.video_codec_id):
                tags.append(video_codec)

        if download_type & DownloadType.AUDIO:
            audio_quality = reversed_audio_quality_map.get(task_info.Download.audio_quality_id)

            if audio_quality and audio_quality != "auto":
                tags.append(Translator.AUDIO_QUALITY(audio_quality))

        if file_ext := self.getFileExtText(task_info):
            tags.append(file_ext)

        return tags

    def getFileExtText(self, task_info: TaskInfo):
        has_video = task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = task_info.Download.type & DownloadType.AUDIO != 0

        if task_info.File.merge_file_ext:
            ext = task_info.File.merge_file_ext

        elif has_audio and not has_video:
            ext = task_info.File.audio_file_ext

        # m4s 只是 DASH 分片的临时扩展名，不是最终产物的格式
        elif has_video and not has_audio and task_info.File.video_file_ext != "m4s":
            ext = task_info.File.video_file_ext

        else:
            ext = ""

        return ext.upper()

    def getAdditionalTagList(self, task_info: TaskInfo):
        download_type = task_info.Download.type

        tag_map = [
            (DownloadType.DANMAKU, "DANMAKU"),
            (DownloadType.SUBTITLE, "SUBTITLES"),
            (DownloadType.COVER, "COVER"),
            (DownloadType.METADATA, "METADATA"),
        ]

        return [Translator.ADDITIONAL_CONTENT_TAG(key) for flag, key in tag_map if download_type & flag]

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

