from qfluentwidgets import SubtitleLabel, BodyLabel, RadioButton

from gui.component.dialog import DialogBase

from util.common.config import config
from util.common.enum import Area

class SelectAreaDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)
        
        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Select Geographic Location"), self)

        desc_lab = BodyLabel(self.tr("Please select your actual location. The program will automatically match a more suitable CDN server accordingly to improve download speed."), self)
        desc_lab.setWordWrap(True)
        tip_lab = BodyLabel(self.tr("Tip: If you are using a proxy, please select the region where the proxy server is located."), self)

        self.cn_radio = RadioButton(self.tr("Mainland China"), self)
        self.cn_radio.setChecked(config.get(config.area) == Area.CN)
        
        self.ov_radio = RadioButton(self.tr("Overseas"), self)
        self.ov_radio.setChecked(config.get(config.area) == Area.OV)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(desc_lab)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.cn_radio)
        self.viewLayout.addWidget(self.ov_radio)
        self.viewLayout.addSpacing(10)

        self.widget.setFixedWidth(450)

    def accept(self):
        if self.cn_radio.isChecked():
            config.set(config.area, Area.CN)

        elif self.ov_radio.isChecked():
            config.set(config.area, Area.OV)

        super().accept()
