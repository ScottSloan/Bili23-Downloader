import wx

import base64
from enum import Enum
from io import BytesIO

from utils.config import Config

class PicID(Enum):
    LeftGirl = 0
    LeftGirlMask = 1
    RightGirl = 2
    RightGirlMask = 3

class Pic:
    def get_pic_bitmap(pic_id: PicID):
        match pic_id:
            case PicID.LeftGirl:
                b64 = Pic.assets_left_girl_pic()

            case PicID.LeftGirlMask:
                b64 = Pic.assets_left_girl_mask_pic()

            case PicID.RightGirl:
                b64 = Pic.assets_right_girl_pic()

            case PicID.RightGirlMask:
                b64 = Pic.assets_right_girl_mask_pic()

        img = BytesIO(base64.b64decode(b64))

        scale_size = Pic.get_scale_size()

        return wx.Image(img).Scale(scale_size[0], scale_size[1]).ConvertToBitmap()
    
    def get_scale_size():
        if Config.Sys.dpi_scale_factor > 1.5:
            return Pic.FromDIP((40, 40))
        else:
            return Pic.FromDIP((80, 80))
        
    def FromDIP(size: tuple):
        scale_factor = Config.Sys.dpi_scale_factor

        return (int(size[0] * scale_factor), int(size[1] * scale_factor))
    
    def assets_left_girl_pic():
        return ""
    
    def assets_left_girl_mask_pic():
        return ""

    def assets_right_girl_pic():
        return ""

    def assets_right_girl_mask_pic():
        return ""