from PySide6.QtCore import QLocale

from qfluentwidgets import ConfigSerializer

from util.common.enum import Language

class LanguageSerializer(ConfigSerializer):
    def serialize(self, language: Language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO
