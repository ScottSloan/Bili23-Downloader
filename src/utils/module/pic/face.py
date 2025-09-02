import os
import wx

from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.io.file import File

class Face:
    @classmethod
    def get_user_face_path(cls):
        Config.User.face_path = os.path.join(Config.User.directory, f"face.jpg")

        if not os.path.exists(Config.User.face_path):
            # 若未缓存头像，则下载头像到本地
            content = RequestUtils.request_get(Config.User.face_url).content

            with open(Config.User.face_path, "wb") as f:
                f.write(content)

        return Config.User.face_path
    
    @classmethod
    def get_user_face_image(cls):
        return wx.Image(cls.get_user_face_path(), wx.BITMAP_TYPE_ANY)
    
    @staticmethod
    def crop_round_face_bmp(image: wx.Image):
        width, height = image.GetSize()
        diameter = min(width, height)

        center = radius = diameter / 2.0
        
        circle_image = wx.Image(diameter, diameter)
        circle_image.InitAlpha()
        
        feather_radius = 1.5
        max_alpha = 255
        
        for y in range(diameter):
            dy = y - center
            for x in range(diameter):
                dx = x - center
                dist = (dx * dx + dy * dy) ** 0.5
                
                if dist <= radius - feather_radius:
                    alpha_val = max_alpha

                elif dist >= radius + feather_radius:
                    alpha_val = 0

                else:
                    ratio = (dist - (radius - feather_radius)) / (2 * feather_radius)
                    alpha_val = int(max_alpha * (1 - ratio))
                
                r, g, b = image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y)
                
                circle_image.SetRGB(x, y, r, g, b)
                circle_image.SetAlpha(x, y, alpha_val)
        
        return circle_image.ConvertToBitmap()

    @staticmethod
    def remove():
        File.remove_file(Config.User.face_path)
    