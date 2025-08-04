import wx

class NumberValidator(wx.Validator):
    def __init__(self):
        wx.Validator.__init__(self)

        self.Bind(wx.EVT_CHAR, self.onCharEVT)
    
    def Clone(self):
        return NumberValidator()
    
    def Validate(self, parent):
        text_ctrl: wx.TextCtrl = parent.GetWindow()

        if text_ctrl.GetValue().isnumeric():
            return True
        else:
            wx.Bell()
            return False
    
    def onCharEVT(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()

        if keycode < wx.WXK_SPACE or keycode == wx.WXK_DELETE:
            event.Skip()

        elif chr(keycode) in self.valid:
            event.Skip()
        else:
            wx.Bell()

    def TransferToWindow(self):
        return True
    
    def TransferFromWindow(self):
        return True
        
class IntCtrl(wx.TextCtrl):
    def __init__(self, parent: wx.Window, size = wx.DefaultSize):
        wx.TextCtrl.__init__(self, parent, -1, size = size, validator = NumberValidator())
