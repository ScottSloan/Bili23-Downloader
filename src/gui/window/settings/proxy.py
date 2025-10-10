import wx
import time
import gettext
from wx.lib.intctrl import IntCtrl
from requests.auth import HTTPProxyAuth

from utils.config import Config
from utils.common.enums import ProxyMode
from utils.common.request import RequestUtils
from utils.common.thread import Thread

from gui.window.settings.page import Page

_ = gettext.gettext

class ProxyPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, _("代理"), 4)

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        proxy_box = wx.StaticBox(self.panel, -1, _("代理设置"))

        proxy_tip = wx.StaticText(proxy_box, -1, _("代理选项"))
        proxy_warning_tip = wx.StaticText(proxy_box, -1, _('注意：使用代理时，请在高级选项卡中\n手动关闭`替换音视频流 CDN 选项`'))

        self.proxy_disable_radio = wx.RadioButton(proxy_box, -1, _("不使用代理"))
        self.proxy_follow_radio = wx.RadioButton(proxy_box, -1, _("跟随系统"))
        self.proxy_custom_radio = wx.RadioButton(proxy_box, -1, _("手动设置"))

        proxy_option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        proxy_option_hbox.Add(self.proxy_disable_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_option_hbox.Add(self.proxy_follow_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_option_hbox.Add(self.proxy_custom_radio, 0, wx.ALL, self.FromDIP(6))

        ip_lab = wx.StaticText(proxy_box, -1, _("地址"))
        self.ip_box = wx.TextCtrl(proxy_box, -1)
        port_lab = wx.StaticText(proxy_box, -1, _("端口"))
        self.port_box = IntCtrl(proxy_box, -1, size = self.FromDIP((80, -1)), min = 1, max = 65535)
        self.port_box.SetLimited(True)

        self.auth_chk = wx.CheckBox(proxy_box, -1, _("启用代理身份验证"))

        uname_lab = wx.StaticText(proxy_box, -1, _("用户名"))
        self.uname_box = wx.TextCtrl(proxy_box, -1)
        pwd_lab = wx.StaticText(proxy_box, -1, _("密码"))
        self.passwd_box = wx.TextCtrl(proxy_box, style = wx.TE_PASSWORD)

        flex_sizer = wx.GridBagSizer(0, 0)
        flex_sizer.Add(ip_lab, pos = (0, 0), flag =  wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.ip_box, pos = (0, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.port_box, pos = (1, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT), border = self.FromDIP(6))
        flex_sizer.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL, border = self.FromDIP(6))
        flex_sizer.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.uname_box, pos = (3, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.passwd_box, pos = (4, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))

        flex_sizer.AddGrowableCol(1)

        self.test_btn = wx.Button(proxy_box, -1, _("测试"), size = self.get_scaled_size((80, 30)))

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
        self.port_box.SetValue(Config.Proxy.proxy_port)
    
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
        Config.Proxy.proxy_port = self.port_box.GetValue()
        Config.Proxy.enable_auth = self.auth_chk.GetValue()
        Config.Proxy.auth_username = self.uname_box.GetValue()
        Config.Proxy.auth_password = self.passwd_box.GetValue()

    def onValidate(self):
        if self.port_box.GetValue() not in range(1, 65536):
            return self.warn(_("端口无效，请输入 1 到 65535 之间的整数"))

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

                url = "https://www.bilibili.com/"
                req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(), proxies = proxy, auth = auth)
                
                end_time = time.time()

                self.show_messagebox(_("测试成功\n\n请求站点：%s\n状态码：%s\n耗时：%ss") % (url, req.status_code, round(end_time - start_time, 1)), _("提示"), wx.ICON_INFORMATION)

            except Exception as e:
                self.show_messagebox(_("测试失败\n\n请求站点：%s\n错误信息：%s") % (url, e), _("提示"), wx.ICON_WARNING)

        proxy = self.get_proxy_option()
        auth = self.get_auth_option()

        Thread(target = test).start()

    def get_proxy_option(self):
        if self.proxy_custom_radio.GetValue():
            proxy = {
                "http": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}",
                "https": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}"
            }
        elif self.proxy_follow_radio.GetValue():
            proxy = None
        else:
            proxy = {}

        return proxy

    def get_auth_option(self):
        if self.auth_chk.GetValue():
            auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.passwd_box.GetValue()
            )
        else:
            auth = HTTPProxyAuth(None, None)

        return auth
    
    def show_messagebox(self, message: str, caption: str, style: int):
        def worker():
            wx.MessageDialog(self, message, caption, style).ShowModal()

        wx.CallAfter(worker)
