import wx
import time
from requests.auth import HTTPProxyAuth

from utils.config import Config
from utils.common.enums import ProxyMode
from utils.common.request import RequestUtils
from utils.common.thread import Thread

from gui.window.settings.page import Page

class ProxyPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, "代理")

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        proxy_box = wx.StaticBox(self.panel, -1, "代理设置")

        proxy_tip = wx.StaticText(proxy_box, -1, "代理选项")
        proxy_warning_tip = wx.StaticText(proxy_box, -1, '注意：使用代理时，请在高级选项卡中\n手动关闭"替换音视频流 CDN"选项')
        
        self.proxy_disable_radio = wx.RadioButton(proxy_box, -1, "不使用代理")
        self.proxy_follow_radio = wx.RadioButton(proxy_box, -1, "跟随系统")
        self.proxy_custom_radio = wx.RadioButton(proxy_box, -1, "手动设置")

        proxy_option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        proxy_option_hbox.Add(self.proxy_disable_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_option_hbox.Add(self.proxy_follow_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_option_hbox.Add(self.proxy_custom_radio, 0, wx.ALL, self.FromDIP(6))
        
        ip_lab = wx.StaticText(proxy_box, -1, "地址")
        self.ip_box = wx.TextCtrl(proxy_box, -1)
        port_lab = wx.StaticText(proxy_box, -1, "端口")
        self.port_box = wx.TextCtrl(proxy_box, -1)

        self.auth_chk = wx.CheckBox(proxy_box, -1, "启用代理身份验证")

        uname_lab = wx.StaticText(proxy_box, -1, "用户名")
        self.uname_box = wx.TextCtrl(proxy_box, -1)
        pwd_lab = wx.StaticText(proxy_box, -1, "密码")
        self.passwd_box = wx.TextCtrl(proxy_box, style = wx.TE_PASSWORD)

        flex_sizer = wx.GridBagSizer(0, 0)
        flex_sizer.Add(ip_lab, pos = (0, 0), flag =  wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.ip_box, pos = (0, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.port_box, pos = (1, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL, border = self.FromDIP(6))
        flex_sizer.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.uname_box, pos = (3, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.passwd_box, pos = (4, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))

        flex_sizer.AddGrowableCol(1)
        
        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.get_scaled_size((80, 30)))

        proxy_sbox = wx.StaticBoxSizer(proxy_box, wx.VERTICAL)
        proxy_sbox.Add(proxy_tip, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        proxy_sbox.Add(proxy_warning_tip, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        proxy_sbox.Add(proxy_option_hbox, 0, wx.EXPAND)
        proxy_sbox.Add(flex_sizer, 0, wx.EXPAND)
        proxy_sbox.Add(self.test_btn, 0, wx.ALL, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(proxy_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def Bind_EVT(self):
        self.proxy_disable_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_follow_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_custom_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)

        self.auth_chk.Bind(wx.EVT_CHECKBOX, self.onChangeAuthEVT)
        
        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestEVT)

    def load_data(self):
        match ProxyMode(Config.Proxy.proxy_mode):
            case ProxyMode.Disable:
                self.proxy_disable_radio.SetValue(True)

            case ProxyMode.Follow:
                self.proxy_follow_radio.SetValue(True)

            case ProxyMode.Custom:
                self.proxy_custom_radio.SetValue(True)

        self.ip_box.SetValue(Config.Proxy.proxy_ip)
        self.port_box.SetValue(str(Config.Proxy.proxy_port) if Config.Proxy.proxy_port is not None else "")
    
        self.auth_chk.SetValue(Config.Proxy.enable_auth)
        self.uname_box.SetValue(Config.Proxy.auth_username)
        self.passwd_box.SetValue(Config.Proxy.auth_password)

        self.onChangeProxyModeEVT(None)
        self.onChangeAuthEVT(None)

    def save_data(self):
        if self.proxy_disable_radio.GetValue():
            proxy = ProxyMode.Disable.value

        elif self.proxy_follow_radio.GetValue():
            proxy = ProxyMode.Follow.value

        else:
            proxy = ProxyMode.Custom.value

        Config.Proxy.proxy_mode = proxy
        Config.Proxy.proxy_ip = self.ip_box.GetValue()
        Config.Proxy.proxy_port = int(self.port_box.GetValue()) if self.port_box.GetValue() != "" else None
        Config.Proxy.enable_auth = self.auth_chk.GetValue()
        Config.Proxy.auth_username = self.uname_box.GetValue()
        Config.Proxy.auth_password = self.passwd_box.GetValue()

    def onValidate(self):
        if not self.port_box.GetValue().isnumeric() and self.proxy_custom_radio.GetValue():
            return self.warn("端口无效")
        
        self.save_data()

    def onChangeProxyModeEVT(self, event: wx.CommandEvent):
        def set_enable(enable: bool):
            self.ip_box.Enable(enable)
            self.port_box.Enable(enable)

        if self.proxy_disable_radio.GetValue():
            set_enable(False)

        elif self.proxy_follow_radio.GetValue():
            set_enable(False)

        else:
            set_enable(True)

    def onChangeAuthEVT(self, event: wx.CommandEvent):
        def set_enable(enable: bool):
            self.uname_box.Enable(enable)
            self.passwd_box.Enable(enable)

        set_enable(self.auth_chk.GetValue())

    def onTestEVT(self, event: wx.CommandEvent):
        def test():
            try:
                start_time = time.time()

                url = "https://www.bilibili.com"
                req = RequestUtils.request_get(url, proxies = proxy, auth = _auth)
                
                end_time = time.time()

                wx.MessageDialog(self, f"测试成功\n\n请求站点：{url}\n状态码：{req.status_code}\n耗时：{round(end_time - start_time, 1)}s", "提示", wx.ICON_INFORMATION).ShowModal()

            except Exception as e:
                wx.MessageDialog(self, f"测试失败\n\n请求站点：{url}\n错误信息：\n\n{e}", "测试代理", wx.ICON_WARNING).ShowModal()

        if self.proxy_custom_radio.GetValue():
            proxy = {
                "http": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}",
                "https": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}"
            }
        else:
            proxy = {}

        if self.auth_chk.GetValue():
            _auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.passwd_box.GetValue()
            )
        else:
            _auth = HTTPProxyAuth(None, None)

        Thread(target = test).start()