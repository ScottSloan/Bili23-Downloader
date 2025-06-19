import wx

class ClipBoard:
    @staticmethod
    def Read():
        text_obj = wx.TextDataObject()

        if not wx.TheClipboard.IsOpened():
            if wx.TheClipboard.Open():
                success = wx.TheClipboard.GetData(text_obj)

                wx.TheClipboard.Close()
            
        if success:
            return text_obj.GetText()

    @staticmethod
    def Write(data: str):
        text_obj = wx.TextDataObject(data)

        if not wx.TheClipboard.IsOpened():
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(text_obj)
        
        wx.TheClipboard.Close()
