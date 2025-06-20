import os
import wx

from utils.config import Config

from utils.common.request import RequestUtils

class FaceUtils:
    @staticmethod
    def check_face_path():
        if not Config.User.face_path:
            _, file_ext = os.path.splitext(Config.User.face_url)

            Config.User.face_path = os.path.join(Config.User.directory, f"face.{file_ext[1:]}")

    @classmethod
    def get_user_face_path(cls):
        cls.check_face_path()

        if not os.path.exists(Config.User.face_path):
            # 若未缓存头像，则下载头像到本地
            content = RequestUtils.request_get(Config.User.face_url).content

            with open(Config.User.face_path, "wb") as f:
                f.write(content)

        return Config.User.face_path
    
    @staticmethod
    def crop_round_face_bmp(image: wx.Image):
        width, height = image.GetSize()
        diameter = min(width, height)
        
        image = image.Scale(diameter, diameter, wx.IMAGE_QUALITY_HIGH)
        
        circle_image = wx.Image(diameter, diameter)
        circle_image.InitAlpha()
        
        for x in range(diameter):
            for y in range(diameter):
                dist = ((x - diameter / 2) ** 2 + (y - diameter / 2) ** 2) ** 0.5
                if dist <= diameter / 2:
                    circle_image.SetRGB(x, y, image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y))
                    circle_image.SetAlpha(x, y, 255)
                else:
                    circle_image.SetAlpha(x, y, 0)
        
        return circle_image.ConvertToBitmap()
    
    @classmethod
    def get_scaled_face(cls, scaled_size: wx.Size):
        width, height = scaled_size

        return wx.Image(cls.get_user_face_path(), wx.BITMAP_TYPE_ANY).Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    