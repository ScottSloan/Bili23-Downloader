import wx

license = """MIT License

Copyright (c) 2022 Scott Sloan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

class LicenseWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "授权")
        
        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        license_box = wx.TextCtrl(self, -1, license, size = self.FromDIP((400, 180)), style = wx.TE_MULTILINE | wx.TE_READONLY)

        close_btn = wx.Button(self, wx.ID_CANCEL, "关闭")

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(license_box, 0, wx.ALL, 10)
        dlg_vbox.Add(close_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, 10)

        self.SetSizerAndFit(dlg_vbox)