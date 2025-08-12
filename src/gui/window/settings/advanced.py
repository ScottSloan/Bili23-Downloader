import wx

from utils.config import Config
from utils.common.map import webpage_option_map

from gui.component.misc.tooltip import ToolTip
from gui.component.text_ctrl.int_ctrl import IntCtrl

from gui.window.settings.page import Page
from gui.dialog.setting.custom_cdn_host import CustomCDNDialog
from gui.dialog.setting.custom_user_agent import CustomUADialog

class AdvancedPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, "高级")

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        cdn_box = wx.StaticBox(self.panel, -1, "CDN 节点设置")

        self.enable_switch_cdn_chk = wx.CheckBox(cdn_box, -1, "替换音视频流 CDN 节点")
        self.enable_custom_cdn_tip = ToolTip(cdn_box)
        self.enable_custom_cdn_tip.set_tooltip("由于哔哩哔哩（B 站）默认分配的 CDN 线路可能存在稳定性问题，导致音视频流下载失败，建议开启`替换音视频流 CDN 节点`功能。该功能会根据您设置的优先级顺序，自动选择可用的 CDN 节点，以提升访问速度和成功率。\n\n请注意：开启代理工具时，请务必关闭此功能，避免 CDN 节点与代理线路冲突导致连接失败。")
        self.custom_cdn_btn = wx.Button(cdn_box, -1, "自定义 CDN 节点", size = self.get_scaled_size((120, 28)))

        custom_cdn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        custom_cdn_hbox.Add(self.enable_switch_cdn_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        custom_cdn_hbox.Add(self.enable_custom_cdn_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        cdn_sbox = wx.StaticBoxSizer(cdn_box, wx.VERTICAL)
        cdn_sbox.Add(custom_cdn_hbox, 0, wx.EXPAND)
        cdn_sbox.Add(self.custom_cdn_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        advanced_download_box = wx.StaticBox(self.panel, -1, "高级下载设置")

        self.download_error_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载出错时自动重试")
        self.download_error_retry_lab = wx.StaticText(advanced_download_box, -1, "重试次数")
        self.download_error_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 1, max = 15)
        self.download_error_retry_unit_lab = wx.StaticText(advanced_download_box, -1, "次")

        download_error_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_error_retry_hbox.AddSpacer(self.FromDIP(20))
        download_error_retry_hbox.Add(self.download_error_retry_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        download_error_retry_hbox.Add(self.download_error_retry_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        download_error_retry_hbox.Add(self.download_error_retry_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.download_suspend_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载停滞时自动重启下载")
        self.download_suspend_retry_lab = wx.StaticText(advanced_download_box, -1, "重启间隔")
        self.download_suspend_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 2, max = 15)
        self.download_suspend_retry_unit_lab = wx.StaticText(advanced_download_box, -1, "秒")

        download_suspend_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_suspend_retry_hbox.AddSpacer(self.FromDIP(20))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_unit_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.always_use_https_protocol_chk = wx.CheckBox(advanced_download_box, -1, "始终使用 HTTPS 发起请求")
        self.custom_ua_btn = wx.Button(advanced_download_box, -1, "自定义 User-Agent", size = self.get_scaled_size((130, 28)))

        advanced_download_sbox = wx.StaticBoxSizer(advanced_download_box, wx.VERTICAL)
        advanced_download_sbox.Add(self.download_error_retry_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        advanced_download_sbox.Add(download_error_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.download_suspend_retry_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        advanced_download_sbox.Add(download_suspend_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.always_use_https_protocol_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        advanced_download_sbox.Add(self.custom_ua_btn, 0, wx.ALL, self.FromDIP(6))

        webpage_box = wx.StaticBox(self.panel, -1, "Web 页面显示设置")

        webpage_lab = wx.StaticText(webpage_box, -1, "显示方式")
        self.webpage_option_choice = wx.Choice(webpage_box, -1, choices = list(webpage_option_map.keys()))
        webpage_tooltip = ToolTip(webpage_box)
        webpage_tooltip.set_tooltip("设置 Web 页面的显示方式\n\n自动检测：自动选择可用的显示方式\n使用系统 Webview 组件：在窗口中内嵌显示页面\n使用系统默认浏览器：在外部浏览器中显示页面")

        webpage_hbox = wx.BoxSizer(wx.HORIZONTAL)
        webpage_hbox.Add(webpage_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        webpage_hbox.Add(self.webpage_option_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        webpage_hbox.Add(webpage_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        ws_port_lab = wx.StaticText(webpage_box, -1, "Websocket 端口")
        self.ws_port_box = IntCtrl(webpage_box, size = self.get_scaled_size((70, 24)))

        ws_port_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ws_port_hbox.Add(ws_port_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        ws_port_hbox.Add(self.ws_port_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        webpage_sbox = wx.StaticBoxSizer(webpage_box, wx.VERTICAL)
        webpage_sbox.Add(webpage_hbox, 0, wx.EXPAND)
        webpage_sbox.Add(ws_port_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(cdn_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(advanced_download_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(webpage_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def Bind_EVT(self):
        self.enable_switch_cdn_chk.Bind(wx.EVT_CHECKBOX, self.onEnableSwitchCDNEVT)
        self.custom_cdn_btn.Bind(wx.EVT_BUTTON, self.onCustomCDNEVT)

        self.download_error_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRetryEVT)
        self.download_suspend_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRestartEVT)

        self.custom_ua_btn.Bind(wx.EVT_BUTTON, self.onCustomUAEVT)

    def load_data(self):
        self.enable_switch_cdn_chk.SetValue(Config.Advanced.enable_switch_cdn)
        Config.Temp.cdn_list = Config.Advanced.cdn_list.copy()

        self.download_error_retry_chk.SetValue(Config.Advanced.retry_when_download_error)
        self.download_error_retry_box.SetValue(Config.Advanced.download_error_retry_count)
        self.download_suspend_retry_chk.SetValue(Config.Advanced.retry_when_download_suspend)
        self.download_suspend_retry_box.SetValue(Config.Advanced.download_suspend_retry_interval)
        self.always_use_https_protocol_chk.SetValue(Config.Advanced.always_use_https_protocol)
        Config.Temp.user_agent = Config.Advanced.user_agent

        self.webpage_option_choice.SetSelection(Config.Advanced.webpage_option)
        self.ws_port_box.SetValue(str(Config.Advanced.websocket_port))

        self.onEnableSwitchCDNEVT(0)
        self.onChangeRetryEVT(0)
        self.onChangeRestartEVT(0)

    def save_data(self):
        Config.Advanced.enable_switch_cdn = self.enable_switch_cdn_chk.GetValue()
        Config.Advanced.cdn_list = Config.Temp.cdn_list.copy()

        Config.Advanced.retry_when_download_error = self.download_error_retry_chk.GetValue()
        Config.Advanced.download_error_retry_count = self.download_error_retry_box.GetValue()
        Config.Advanced.retry_when_download_suspend = self.download_suspend_retry_chk.GetValue()
        Config.Advanced.download_suspend_retry_interval = self.download_suspend_retry_box.GetValue()
        Config.Advanced.always_use_https_protocol = self.always_use_https_protocol_chk.GetValue()
        Config.Advanced.user_agent = Config.Temp.user_agent

        Config.Advanced.webpage_option = self.webpage_option_choice.GetSelection()
        Config.Advanced.websocket_port = int(self.ws_port_box.GetValue())

    def onValidate(self):
        if not self.ws_port_box.GetValue().isnumeric():
            return self.warn("Websocket 端口无效")
        
        self.save_data()
    
    def onEnableSwitchCDNEVT(self, event: wx.CommandEvent):
        self.custom_cdn_btn.Enable(self.enable_switch_cdn_chk.GetValue())

    def onCustomCDNEVT(self, event: wx.CommandEvent):
        dlg = CustomCDNDialog(self)
        dlg.ShowModal()

    def onChangeRetryEVT(self, event: wx.CommandEvent):
        enable = self.download_error_retry_chk.GetValue()

        self.download_error_retry_lab.Enable(enable)
        self.download_error_retry_box.Enable(enable)
        self.download_error_retry_unit_lab.Enable(enable)

    def onChangeRestartEVT(self, event: wx.CommandEvent):
        enable = self.download_suspend_retry_chk.GetValue()

        self.download_suspend_retry_lab.Enable(enable)
        self.download_suspend_retry_box.Enable(enable)
        self.download_suspend_retry_unit_lab.Enable(enable)

    def onCustomUAEVT(self, event: wx.CommandEvent):
        dlg = CustomUADialog(self)
        dlg.ShowModal()