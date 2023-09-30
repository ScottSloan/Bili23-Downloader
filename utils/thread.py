import ctypes
import threading
from typing import List

class Thread(threading.Thread):
    def __init__(self, target = None, args = (), kwargs = None, name = ""):
        threading.Thread.__init__(self, target = target, args = args, kwargs = kwargs, name = name)

        self.kernel32 = ctypes.windll.kernel32
    
    def stop(self):    
        ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, ctypes.py_object(SystemExit))
    
    def start(self):
        threading.Thread.start(self)
    
    def pause(self):
        handle = self.kernel32.OpenThread(0x0002, False, self.ident)
        self.kernel32.SuspendThread(handle)
        self.kernel32.CloseHandle(handle)

    def resume(self):
        handle = self.kernel32.OpenThread(0x0002, False, self.ident)
        self.kernel32.ResumeThread(handle)
        self.kernel32.CloseHandle(handle)

class ThreadPool:
    def __init__(self):
        self.thread_list: List[Thread] = []

    def submit(self, target, args):
        new = Thread(target = target, args = args)
        new.setDaemon(True)

        self.thread_list.append(new)

    def pause(self):
        for thread in self.thread_list:
            thread.pause()

    def resume(self):
        for thread in self.thread_list:
            thread.resume()

    def start(self):
        for thread in self.thread_list:
            thread.start()

    def stop(self):
        for thread in self.thread_list:
            thread.stop()
        
        self.thread_list.clear()

    def wait(self):
        for thread in self.thread_list:
            thread.join()