import wx

from utils.common.request import RequestUtils
from utils.common.thread import Thread

from gui.dialog.cover import CoverViewerDialog

class CoverUtils:
    @classmethod
    def view_cover(cls, parent, cover: str):
        def worker():
            wx.CallAfter(show_dialog, cls.get_cover_raw_contents(cover))

        def show_dialog(raw_contents: bytes):
            dlg = CoverViewerDialog(parent, raw_contents)
            dlg.Show()

        Thread(target = worker).start()

    @staticmethod
    def get_cover_raw_contents(cover: str):
        req = RequestUtils.request_get(cover)

        return req.content

    @staticmethod
    def save_cover_file():
        pass