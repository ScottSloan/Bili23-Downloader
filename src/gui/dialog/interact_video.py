import wx
import os
import json

from gui.component.dialog import Dialog

class InteractVideoDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "互动视频")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.current_node_lab = wx.StaticText(self, -1, "当前节点：")
        
        self.options_list = wx.ListCtrl(self, -1, size = self.FromDIP((400, 150)), style = wx.LC_ICON)
        self.options_list.EnableCheckBoxes(True)

        self.back_btn = wx.Button(self, -1, "返回上一节点")

        left_vbox = wx.BoxSizer(wx.VERTICAL)
        left_vbox.Add(self.current_node_lab, 0, wx.ALL, 10)
        left_vbox.Add(self.options_list, 0, wx.ALL & (~wx.TOP), 10)
        left_vbox.Add(self.back_btn, 0, wx.ALL & (~wx.TOP), 10)

        nodes_lab = wx.StaticText(self, -1, "节点列表")
        self.nodes_list = wx.ListCtrl(self, -1, size = self.FromDIP(10), style = wx.LC_REPORT)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(nodes_lab, 0, wx.ALL, 10)
        right_vbox.Add(self.nodes_list, 0, wx.ALL & (~wx.TOP), 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_vbox, 0, wx.EXPAND, 10)
        hbox.Add(right_vbox, 0, wx.EXPAND, 10)

        self.SetSizerAndFit(hbox)
        
    def init_utils(self):    
        def init_nodes_list():
            self.nodes_list.AppendColumn("节点名称")

            path = os.path.join(os.getcwd(), "node.json")

            with open(path, "r", encoding = "utf-8") as f:
                data = json.loads(f.read())

            for entry in data["nodes"]:
                self.nodes_list.Append([entry.get("title")])
        
        init_nodes_list()

