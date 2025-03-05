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
        self.error_retry_count = 0
        self.thread_alive_count = 0

        self.current_total_size = 0

        self._e = None
        self._downloader_info_list = []
        self.thread_info = {}

        # 判断是否为断点续传
        if not self.task_info.completed_size:
            self.completed_size = 0
            self.current_completed_size = 0
        else:
            self.completed_size = self.task_info.completed_size
            self.current_completed_size = self.task_info.current_completed_size

    def start_download(self, downloader_info_list: List[dict]):
        def add_url(download_info: DownloaderInfo):
            def _get_range_list(file_size: int, thread_count: int):
                # 计算分片下载区间
                piece_size = int(file_size / thread_count)
                _range_list = []

                for i in range(thread_count):
                    start = i * piece_size + 1 if i != 0 else 0
                    end = (i + 1) * piece_size if i != thread_count - 1 else file_size

                    _range_list.append([start, end])

                return _range_list

            def _get_range_list_from_file(type: str):
                # 从文件读取分片下载区间
                _range_list = []

                if type in self.thread_info:
                    for value in self.thread_info[type].values():
                        _range_list.append(value["range"])

                    return _range_list
                
                else:
                    # 不存在断点续传信息，重新下载
                    pass

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
            
            def get_range_list_ex(_file_size: int):
                if self.current_completed_size:
                    self.thread_info = self.file_tool.get_thread_info()

                    return _get_range_list_from_file(download_info.type)
                else:
                    self.thread_info = {}

                    return _get_range_list(_file_size, _get_thread_count(_file_size))

            file_path = os.path.join(Config.Download.path, download_info.file_name)

            download_url, self.current_total_size = self.get_file_size(download_info.url_list, self.task_info.referer_url, file_path)

            range_list = get_range_list_ex(self.current_total_size)

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

        def get_total_size():
            # 获取总大小
            if not self.task_info.total_size:
                for entry in self._downloader_info_list:
                    (url, size) = self.get_file_size(entry["url_list"], self.task_info.referer_url)

                    self.task_info.total_size += size

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

        def worker():
            reset()

            self._downloader_info_list = downloader_info_list

            get_total_size()

            entry = self._downloader_info_list[:1]

            if not entry:
                self.onFinished()
                return
            else:
                entry = entry[0]

            _info = DownloaderInfo()
            _info.load_from_dict(entry)

            add_url(_info)

            # 开启线程池和监听线程
            self.ThreadPool.start()
            self.listen_thread.start()

            if not self.completed_size:
                # 回调 onStart，UI 更新下载信息
                self.callback.onStartCallback()
        
        try:
            worker()

        except Exception as e:
            self._e = e
            self.onError()

    def range_download(self, info: RangeDownloadInfo):
        def limit_speed():
            if Config.Download.enable_speed_limit:
                # 计算执行时间
                elapsed_time = time.time() - start_time
                expected_time = self.current_completed_size / speed_bps

                if elapsed_time < expected_time:
                    # 计算应暂停的时间，从而限制下载速度
                    time.sleep(expected_time - elapsed_time)

        def check_flag():
            if self.current_completed_size >= self.current_total_size:
                # 下载完成，置标志位为 True
                self.range_thread_stop_flag = True
                self.finish_flag = True

        # 分片下载
        try:
            req = self.session.get(RequestTool.replace_protocol(info.url), headers = RequestTool.get_headers(info.referer_url, Config.User.SESSDATA, info.range), stream = True, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
            
            with open(info.file_path, "rb+") as f:
                speed_bps = Config.Download.speed_mbps * 1024 * 1024
                chunk_size = 1024
                f.seek(info.range[0])

                start_time = time.time()

                if self.current_completed_size:
                    # 断点续传时补偿 start_time
                    start_time -= self.current_completed_size / speed_bps

                for chunk in req.iter_content(chunk_size = chunk_size):
                    if chunk:
                        if self.range_thread_stop_flag:
                            # 检测分片下载停止标志位
                            break

                        f.write(chunk)
                        f.flush()

                        self.completed_size += len(chunk)
                        self.current_completed_size += len(chunk)

                        self.thread_info[info.type][info.index]["range"][0] += len(chunk)

                        check_flag()

                        limit_speed()

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

            if self.retry_count == Config.Advanced.download_suspend_retry_interval:
                self._e = GlobalException("下载失败超过最大重试次数")

                self.onError()
                
        def update_download_file_info():
            self.task_info.progress = info["progress"]
            self.task_info.completed_size = self.completed_size
            self.task_info.current_completed_size = self.current_completed_size

            kwargs = {
                "progress": info["progress"],
                "completed_size": self.completed_size,
                "current_completed_size": self.current_completed_size
            }

            self.file_tool.update_task_info_kwargs(**kwargs)
            self.file_tool.update_thread_info(self.thread_info)

        def update():
            # 更新下载进度到文件，并回调UI更新进度
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
        self.start_download(self._downloader_info_list)

        # 启动监听线程
        self.listen_thread = Thread(target = self.onListen, name = "ListenThread")

        self.listen_thread.start()

    def onStop(self):
        # 停止下载
        self.range_thread_stop_flag = True
        self.listen_stop_flag = True

        self.session.close()

    def onFinished(self):
        def update_download_file_info():
            kwargs = {
                "item_flag": self.task_info.item_flag
            }

            self.file_tool.update_task_info_kwargs(**kwargs)

        def update_item_flag():
            if self._downloader_info_list:
                entry = self._downloader_info_list[:1][0]

                self.task_info.item_flag.remove(entry["type"])
                self._downloader_info_list = self._downloader_info_list[1:]

        update_item_flag()

        update_download_file_info()

        if self.task_info.item_flag:
            # 如果还存在下载项目，则继续下载
            self.current_completed_size = 0
            
            self.start_download(self._downloader_info_list)
        
        if self.completed_size >= self.task_info.total_size:
            # 下载完成，回调 onMerge 进行合成
            self.listen_stop_flag = True

            self.callback.onMergeCallback()
    
    def onError(self):
        # 关闭线程池和监听线程，停止下载
        self.onStop()

        if self.error_retry_count <= Config.Advanced.download_error_retry_count:
            self.error_retry_count += 1
            
            self.onResume()

            return

        try:
            raise self._e
        
        except Exception as e:
            raise GlobalException(e, callback = self.callback.onErrorCallback) from e
    
    def get_file_size(self, url_list: list, referer_url: str, path: str = None):
        def truncate_file():
            if path:
                # 判断本地文件是否存在
                if not os.path.exists(path):
                    with open(path, "wb") as f:
                        # 使用 seek 方法，移动文件指针，快速有效，完美解决大文件创建耗时的问题
                        f.seek(total_size - 1)
                        f.write(b"\0")
        
        def get_cdn_list():
            if Config.Advanced.enable_custom_cdn:
                match CDNMode(Config.Advanced.custom_cdn_mode):
                    case CDNMode.Auto:
                        _temp_cdn_map_list = sorted(list(cdn_map.values()), key = lambda x: x["order"], reverse = False)

                        return [entry["cdn"] for entry in _temp_cdn_map_list]
                    
                    case CDNMode.Custom:
                        return [Config.Advanced.custom_cdn]
            else:
                return [None]

        def switch_cdn(url: str, cdn: str):
            if cdn:
                return re.sub(r'(?<=https://)[^/]+', cdn, url)
            else:
                return url
            
        def request_head(url: str, cdn: str):
            url_with_cdn = switch_cdn(url, cdn)
            
            return url_with_cdn, self.session.head(url_with_cdn, headers = RequestTool.get_headers(referer_url), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
    
        for url in url_list:
            for cdn in get_cdn_list():
                url_with_cdn, req = request_head(url, cdn)

                if "Content-Length" in req.headers:
                    total_size = int(req.headers["Content-Length"])

                    if total_size:
                        truncate_file()

                        return url_with_cdn, total_size