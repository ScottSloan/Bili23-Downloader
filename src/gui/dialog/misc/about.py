from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtCore import qVersion

from qfluentwidgets import SubtitleLabel, BodyLabel, TransparentPushButton, FluentIcon, __version__

from gui.dialog.misc import TermsOfUseDialog
from gui.component.dialog import DialogBase

from util.common import config

from datetime import datetime
import webbrowser

class AboutDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        app_name = config.app_name
        app_version = config.app_version
        year = datetime.now().year

        self.caption_lab = SubtitleLabel(self.tr("About {app_name}").format(app_name = app_name), self)

        self.app_version_lab = BodyLabel(self.tr("Version {app_version}").format(app_version = app_version), self)
        self.qt_version_lab = BodyLabel(self.tr("Powered by Qt {qt_version} and QFluentWidgets {qfluentwidgets_version}").format(qt_version = qVersion(), qfluentwidgets_version = __version__), self)
        self.license_lab = BodyLabel(self.tr("This software is free and open-source, licensed under the GNU General Public License v3 (GPLv3)."))
        self.copyright_lab = BodyLabel(self.tr("Copyright © 2022-{year} Scott Sloan. All Rights Reserved.").format(year = year))

        self.sponsor_lab = BodyLabel(self.tr("If this project saved you time or solved your problem, consider buying the author a coffee! Don't forget to star the repository on GitHub to support open-source development."))
        self.sponsor_lab.setWordWrap(True)

        self.terms_btn = TransparentPushButton(FluentIcon.DOCUMENT, self.tr("Terms of Use"), self)
        self.documentation_btn = TransparentPushButton(FluentIcon.HELP, self.tr("Documentation"), self)
        self.github_btn = TransparentPushButton(FluentIcon.GITHUB, self.tr("Github"), self)
        self.sponsor_btn = TransparentPushButton(FluentIcon.HEART, self.tr("Sponsor"), self)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.app_version_lab)
        content_layout.addWidget(self.qt_version_lab)
        content_layout.addSpacing(10)
        content_layout.addWidget(self.license_lab)
        content_layout.addSpacing(10)
        content_layout.addWidget(self.copyright_lab)
        content_layout.addSpacing(30)
        content_layout.addWidget(self.sponsor_lab)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.terms_btn)
        button_layout.addWidget(self.documentation_btn)
        button_layout.addWidget(self.github_btn)
        button_layout.addWidget(self.sponsor_btn)
        button_layout.addStretch()

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(content_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(button_layout)

        self.hideCancelButton()

        self.widget.setMinimumWidth(600)

        self.connect_signals()

    def connect_signals(self):
        self.terms_btn.clicked.connect(self.on_terms)
        self.documentation_btn.clicked.connect(self.on_ducumation)
        self.github_btn.clicked.connect(self.on_github)
        self.sponsor_btn.clicked.connect(self.on_sponsor)

    def on_terms(self):
        dialog = TermsOfUseDialog(self)
        dialog.exec()

    def on_ducumation(self):
        webbrowser.open("https://bili23.scott-sloan.cn/doc/introduction.html")

    def on_github(self):
        webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader")

    def on_sponsor(self):
        webbrowser.open("https://bili23.scott-sloan.cn/doc/about.html")
