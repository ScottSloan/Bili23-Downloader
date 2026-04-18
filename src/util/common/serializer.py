from PySide6.QtCore import QLocale

from qfluentwidgets import ConfigSerializer

from .enum import Language, Scaling

class LanguageSerializer(ConfigSerializer):
    def serialize(self, language: Language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO

class ScalingSerializer(ConfigSerializer):
    def serialize(self, scaling: Scaling):
        return scaling.value if scaling != Scaling.AUTO else "Auto"

    def deserialize(self, value: str):
        return Scaling(value) if value != "Auto" else Scaling.AUTO