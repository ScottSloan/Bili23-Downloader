import wx
import io

from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.thread import Thread
from utils.common.enums import CoverType

class Cover:
    @classmethod
    def view_cover(cls, parent, cover_url: str):
        def worker():
            wx.CallAfter(show_dialog, cls.get_cover_raw_contents(cover_url))

        def show_dialog(raw_contents: bytes):
            from gui.dialog.cover_viewer import CoverViewerDialog

            dlg = CoverViewerDialog(parent, raw_contents, cover_url)
            dlg.Show()

        Thread(target = worker).start()

    @staticmethod
    def get_cover_raw_contents(cover_url: str):
        req = RequestUtils.request_get(cover_url)

        return req.content

    @classmethod
    def download_cover(cls, cover_url: str, cover_type: int = Config.Basic.cover_file_type):
        url = f"{cover_url}@{cls.get_cover_type(cover_type)}"

        return cls.get_cover_raw_contents(url)
            
    @staticmethod
    def get_cover_type(cover_type: int = Config.Basic.cover_file_type):
        match CoverType(cover_type):
            case CoverType.JPG:
                return ".jpg"
            
            case CoverType.PNG:
                return ".png"
            
            case CoverType.WEBP:
                return ".webp"
            
            case CoverType.AVIF:
                return ".avif"
    
    @staticmethod
    def get_image_obj(cover_raw_contents: bytes) -> wx.Image:
        return wx.Image(io.BytesIO(cover_raw_contents))

    @classmethod
    def get_cover_size(cls, cover_raw_contents: bytes):
        return cls.get_image_obj(cover_raw_contents).GetSize()

    @classmethod
    def get_scaled_size(cls, cover_raw_contents: bytes, new_size: wx.Size):
        cover_image = cls.get_image_obj(cover_raw_contents)

        width, height = cover_image.GetSize()

        width_ratio = new_size.width / width
        height_ratio = new_size.height / height

        ratio = min(width_ratio, height_ratio)

        return wx.Size(int(width * ratio), int(height * ratio))

    @classmethod
    def get_scaled_bitmap(cls, cover_raw_contents: bytes, new_size: wx.Size):
        image = cls.get_image_obj(cover_raw_contents)

        return cls.get_scaled_bitmap_from_image(image, new_size)
    
    @staticmethod
    def get_scaled_bitmap_from_image(image: wx.Image, new_size: wx.Size):
        return image.Rescale(new_size.width, new_size.height, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
    
    @classmethod
    def crop_cover(cls, cover_raw_contents: bytes):
        image = cls.get_image_obj(cover_raw_contents)

        width, height = image.GetSize()

        if width * 9 > height * 16:
            new_width = round(height * 16 / 9)

            x_offset = (width - new_width) // 2

            return image.GetSubImage(wx.Rect((x_offset, 0, new_width, height)))
        
        elif width * 9 < height * 16:
            new_height = round(width * 9 / 16)

            y_offset = (height - new_height) // 2

            return image.GetSubImage(wx.Rect(0, y_offset, width, new_height))
        
        else:
            return image
