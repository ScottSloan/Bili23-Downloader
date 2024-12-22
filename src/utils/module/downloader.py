import os
import re
import time
import requests
from typing import List

from utils.config import Config
from utils.tool_v2 import RequestTool, DownloadFileTool
from utils.common.thread import Thread, ThreadPool
from utils.common.data_type import DownloadTaskInfo, DownloaderCallback, ThreadInfo, DownloaderInfo, RangeDownloadInfo
from utils.common.map import cdn_map
from utils.common.enums import CDNMode
from utils.common.exception import GlobalException

class Downloader:
    def __init__(self, task_info: DownloadTaskInfo, file_tool: DownloadFileTool, callback: DownloaderCallback):
        self.task_info, self.file_tool, self.callback = task_info, file_tool, callback

        self.init_utils()

    def init_utils(self):
        self.ThreadPool = ThreadPool()

        # 创建持久化 Session
        self.session = requests.Session()

        # 初始化错误标志位 + 下载完成标志位
        self.error_flag = False
        self.finish_flag = False

        # 初始化重试计数器
        self.retry_count = 0
        self.thread_alive_count = 0

        self._e = None

        # 判断是否为断点续传
        if not self.task_info.completed_size:
            self.completed_size = 0

            self.thread_info = {}
        else:
            self.completed_size = self.task_info.completed_size

            self.thread_info = self.file_tool.get_thread_info()

    def start_download(self, downloader_info_list: List[dict]):
        def add_url(download_info: DownloaderInfo):
            def get_range_list(file_size: int, thread_count: int):
                # 计算分片下载区间
                piece_size = int(file_size / thread_count)
                _range_list = []

                for i in range(thread_count):
                    start = i * piece_size + 1 if i != 0 else 0
                    end = (i + 1) * piece_size if i != thread_count - 1 else file_size

                    _range_list.append([start, end])

                return _range_list

            def get_range_list_from_file(type: str):
                # 从文件读取分片下载区间
                _range_list = []

                for value in self.thread_info[type].values():
                    _range_list.append(value["range"])

                return _range_list

            def _get_range_download_info():
                # 创建 RangeDownloadInfo
                _range_info = RangeDownloadInfo()
                _range_info.index = str(index)
                _range_info.type = download_info.type
                _range_info.url = download_url
                _range_info.referer_url = self.task_info.referer_url
                _range_info.file_path = file_path
                _range_info.range = _range

                return _range_info
            
            def _get_thread_count(_file_size: int):
                # 小于 10 MB 的文件只开启 1 个线程下载
                if _file_size < 10 * 1024 * 1024:
                    return 1
                else:
                    return Config.Download.max_thread_count

            file_path = os.path.join(Config.Download.path, download_info.file_name)

            try:
                download_url, file_size = self.get_file_size(download_info.url_list, self.task_info.referer_url, file_path)

            except Exception as e:
                self._e = e
                self.onError()

            if self.completed_size:
                range_list = get_range_list_from_file(download_info.type)
            else:
                range_list = get_range_list(file_size, _get_thread_count(file_size))
                self.task_info.total_size += file_size

            self.thread_alive_count += len(range_list)

            if download_info.type not in self.thread_info:
                self.thread_info[download_info.type] = {}

            for index, _range in enumerate(range_list):
                if _range[0] < _range[1]:
                    # 同步创建 thread_info
                    _thread_info = ThreadInfo()
                    _thread_info.file_name = download_info.file_name
                    _thread_info.range = _range

                    self.thread_info[download_info.type][str(index)] = _thread_info.to_dict()

                    _range_info = _get_range_download_info()

                    self.ThreadPool.submit(self.range_download, args = (_range_info, ))

        def reset():
            # 创建监听线程
            self.listen_thread = Thread(target = self.onListen, name = "ListenThread")

            self.ThreadPool = ThreadPool()
            
            self.session = requests.Session()

            # 重置标识符
            self.listen_stop_flag = False
            self.range_thread_stop_flag = False

            self.error_flag = False
            self.finish_flag = False

            self.retry_count = 0

        reset()

        # 添加下载链接
        for entry in downloader_info_list:
            _info = DownloaderInfo()
            _info.load_from_dict(entry)

            add_url(_info)

        # 开启线程池和监听线程
        self.ThreadPool.start()
        self.listen_thread.start()

        if not self.completed_size:
            # 回调 onStart，UI 更新下载信息
            self.callback.onStartCallback(self.task_info.total_size)

    def range_download(self, info: RangeDownloadInfo):
        def limit_speed():
            if Config.Download.enable_speed_limit:
                # 计算执行时间
                limit_bytes = Config.Download.speed_limit_in_mb * 1024 * 1024

                elapsed_time = time.time() - start_time
                expected_time = chunk_size / (limit_bytes / self.thread_alive_count)

                if elapsed_time < 1:
                    # 计算应暂停的时间，从而限制下载速度
                    time.sleep(max(0, expected_time - elapsed_time))

                    return time.time()

        def check_flag():
            if self.completed_size >= self.task_info.total_size:
                # 下载完成，置标志位为 True
                self.range_thread_stop_flag = True
                self.finish_flag = True

        # 分片下载
        try:
            req = self.session.get(info.url, headers = RequestTool.get_headers(info.referer_url, Config.User.sessdata, info.range), stream = True, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
            
            with open(info.file_path, "rb+") as f:
                start_time = time.time()
                chunk_size = 8192
                f.seek(info.range[0])

                for chunk in req.iter_content(chunk_size = chunk_size):
                    if chunk:
                        if self.range_thread_stop_flag:
                            # 检测分片下载停止标志位
                            break

                        f.write(chunk)
                        f.flush()

                        self.completed_size += len(chunk)
                        self.thread_info[info.type][info.index]["range"][0] += len(chunk)

                        check_flag()

                        start_time = limit_speed()

        except Exception as e:
            # 置错误标志位为 True
            self.error_flag = True
            self._e = e

            # 停止线程
            return
        
        self.thread_alive_count -= 1

    def onListen(self):
        def get_progress_info():
            # 记录下载信息
            return {
                "progress": int(self.completed_size / self.task_info.total_size * 100),
                "speed": self.completed_size - _temp_size,
                "completed_size": self.completed_size
            }

        def retry():
            if info["speed"] <= 0:
                self.retry_count += 1

            if self.retry_count == 5:
                self.onStop()

                # self.restart()

        def update_download_file_info():
            kwargs = {
                "progress": info["progress"],
                "completed_size": self.completed_size
            }

            self.file_tool.update_task_info_kwargs(**kwargs)
            self.file_tool.update_thread_info(self.thread_info)

        def update():
            update_download_file_info()

            self.callback.onDownloadCallback(info)

        # 监听线程，负责监听下载进度
        while not self.listen_stop_flag:
            _temp_size = self.completed_size

            time.sleep(1)
            
            info = get_progress_info()

            retry()

             # 检测停止标志位
            if self.listen_stop_flag:
                update_download_file_info()
                break
            
            # 检测错误标志位，回调下载失败函数
            if self.error_flag:
                self.onError()
                break
            
            # 检测下载完成标志位
            if self.finish_flag:
                update()

                self.onFinished()
                
                break
            
            update()

    def onPause(self):
        # 暂停下载
        self.onStop()

    def onResume(self):
        # 恢复下载
        self.start_download()

        # 启动监听线程
        self.listen_thread = Thread(target = self.onListen, name = "ListenThread")

        self.listen_thread.start()

    def onStop(self):
        # 停止下载
        self.range_thread_stop_flag = True
        self.listen_stop_flag = True

        self.session.close()

    def onFinished(self):
        # 下载完成，回调 onMerge 进行合成
        self.listen_stop_flag = True

        self.callback.onMergeCallback()
    
    def onError(self):
        # 关闭线程池和监听线程，停止下载
        self.onStop()

        try:
            raise self._e
        
        except Exception as e:
            raise GlobalException(e, callback = self.callback.onErrorCallback, use_traceback = True)
    
    def get_file_size(self, url_list: list, referer_url: str, path: str):
        def request_head_gen():
            for url in url_list:
                req = self.session.head(url, headers = RequestTool.get_headers(referer_url), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
                yield url, req.headers
        
        total_size = None

        for url, headers in request_head_gen():
            # 检测 headers 是否包含 Content-Length，不包含的链接属于无效链接
            if "Content-Length" in headers:
                total_size = int(headers["Content-Length"])

                if total_size:
                    break

        if not total_size:
            if Config.Download.enable_custom_cdn and Config.Download.custom_cdn_mode == CDNMode.Auto.value:
                return self.get_file_size(next(self.switch_cdn(url_list)), referer_url, path)

        # 判断本地文件是否存在
        if not os.path.exists(path):
            with open(path, "wb") as f:
                # 使用 seek 方法，移动文件指针，快速有效，完美解决大文件创建耗时的问题
                f.seek(total_size - 1)
                f.write(b"\0")
        
        # 返回可以正常下载的链接
        return (url, total_size)

    def switch_cdn(self, url_list: list):
        def _replace(url: str, cdn: str):
            return re.sub(r'(?<=https://)[^/]+', cdn, url)

        for cdn in cdn_map.values():
            yield [_replace(url, cdn) for url in url_list]