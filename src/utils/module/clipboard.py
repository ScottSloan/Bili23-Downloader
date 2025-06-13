import wx

class ClipBoard:
    @staticmethod
    def Read():
        text_obj = wx.TextDataObject()

        if wx.TheClipboard.Open():
            if wx.TheClipboard.GetData(text_obj):
                wx.TheClipboard.Close()
                
                return text_obj.GetText()

    @staticmethod
    def Write(data: str):
        text_obj = wx.TextDataObject(data)

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(text_obj)
