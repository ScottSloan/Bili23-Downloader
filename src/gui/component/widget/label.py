from qfluentwidgets import FluentLabelBase, getFont

class SectionLabel(FluentLabelBase):
    """
    SectionLabel 用于显示分区标题，字体大小 16pt，介于 BodyLabel (14pt) 和 SubtitleLabel (20pt) 之间。
    """

    def getFont(self):
        return getFont(16)
