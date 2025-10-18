from abc import ABC, abstractmethod

from utils.common.model.data_type import Process

class Callback(ABC):
    @staticmethod
    @abstractmethod
    def onSuccess(*process: Process):
        pass
    
    @staticmethod
    @abstractmethod
    def onError(*process: Process):
        pass

class ParseCallback(ABC):
    @staticmethod
    @abstractmethod
    def onError():
        pass
    
    @staticmethod
    @abstractmethod
    def onJump(url: str):
        pass
    
    @staticmethod
    @abstractmethod
    def onUpdateName(name: str):
        pass

    @staticmethod
    @abstractmethod
    def onUpdateTitle(title: str):
        pass

class DownloaderCallback(ABC):
    @staticmethod
    @abstractmethod
    def onStart():
        pass
    
    @staticmethod
    @abstractmethod
    def onDownloading(speed: str):
        pass
    
    @staticmethod
    @abstractmethod
    def onComplete():
        pass
    
    @staticmethod
    @abstractmethod
    def onError():
        pass

class PlayerCallback(ABC):
    @staticmethod
    @abstractmethod
    def onLengthChange(length: int):
        pass

    @staticmethod
    @abstractmethod
    def onReset():
        pass

class ConsoleCallback(ABC):
    @staticmethod
    @abstractmethod
    def onReadOutput(output: str):
        pass

    @staticmethod
    @abstractmethod
    def onSuccess(process):
        pass

    @staticmethod
    @abstractmethod
    def onError(process):
        pass

class LiveRecordingCallback(ABC):
    @staticmethod
    @abstractmethod
    def onRecording(speed: str):
        pass