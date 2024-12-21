import ctypes
import threading
from typing import List

class Thread(threading.Thread):
    def __init__(self, target = None, args = (), kwargs = None, name = "", daemon = True):
        threading.Thread.__init__(self, target = target, args = args, kwargs = kwargs, name = name, daemon = daemon)
    
    def stop(self):
        # 使用 Python C API 强制停止线程
        ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, ctypes.py_object(SystemExit))
    
    def start(self):
        threading.Thread.start(self)
    
class ThreadPool:
    def __init__(self):
        self.thread_list: List[Thread] = []

    def submit(self, target, args):
        new = Thread(target = target, args = args)
        
        self.thread_list.append(new)

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