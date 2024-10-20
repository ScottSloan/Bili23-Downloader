import os
import wx
import time
import json
import requests
from requests.adapters import HTTPAdapter
from typing import Optional

from utils.config import Config
from utils.tools import get_header, get_proxy, get_auth, format_size
from utils.thread import Thread, ThreadPool

class Downloader:
    def __init__(self, info, onStart, onDownload, onMerge, onError):
        self.info, self.onStart, self.onDownload, self.onMerge, self.onErrorEx = info, onStart, onDownload, onMerge, onError

        self.init_utils()

    def init_utils(self):
        # 初始化变量
        self.total_size = 0
        self.completed_size = 0

        # 创建监听线程
        self.listen_thread = Thread(target = self.onListen, name = "ListenThread", daemon = True)

        # 创建持久化 Session
        self.session = requests.Session()

        # 出错重连机制
        self.session.mount("http://", HTTPAdapter(max_retries = 5))
        self.session.mount("https://", HTTPAdapter(max_retries = 5))
        
        self.ThreadPool = ThreadPool()

        # 初始化停止标志位，包含监听线程停止标志位和分片下载停止标志位
        self.stop_flag = False
        self.range_stop_flag = False

        # 初始化错误标志位 + 下载完成标志位
        self.error_flag = False
        self.finish_flag = False

        # 初始化重试计数器
        self.retry_count = 0

        self.thread_info = {}
        self.thread_alive_count = 0

        self.download_info = DownloaderInfo()

        if not self.info["flag"]:
            self.download_info.init_info(self.info)
        else:
            # 断点续传，直接读取数据
            contents = self.download_info.read_info()
            base_info = contents[str(self.info["id"])]["base_info"]
            thread_info = contents[str(self.info["id"])]["thread_info"]

            self.download_info.id = self.download_id = base_info["id"]

            if base_info["total_size"]:
                self.total_size = base_info["total_size"]
                self.completed_size = self.download_info.calc_completed_size(self.total_size, thread_info)
                self.thread_info = contents[str(self.info["id"])]["thread_info"]

    def add_url(self, info: dict):
        path = os.path.join(Config.Download.path, info["file_name"])

        durl, file_size = self.get_total_size(info["url"], info["referer_url"], path)
        self.total_size += file_size

        # 音频文件较小，使用 2 线程下载
        chunk_list = self.get_chunk_list(file_size, Config.Download.max_thread_count if info["type"] == "video" else 2)
        self.thread_alive_count += len(chunk_list)

        for index, chunk_list in enumerate(chunk_list):
            url, referer_url, temp = durl, info["referer_url"], info.copy()

            thread_id = f"{info['type']}_{info['id']}_{index + 1}"
            temp["chunk_list"] = chunk_list
            self.thread_info[thread_id] = temp

            self.download_id = info["id"]
            
            self.ThreadPool.submit(self.range_download, args = (thread_id, url, referer_url, path, chunk_list,))

    def start(self, info: list):
        # 添加下载链接
        for entry in info:
            self.add_url(entry)

        self.update_total_size(self.total_size)

        # 开启线程池和监听线程
        self.ThreadPool.start()
        self.listen_thread.start()

        # 回调 onStart，UI 更新下载信息
        wx.CallAfter(self.onStart)

    def restart(self):
        # 重置停止线程标志位
        self.stop_flag = False
        self.range_stop_flag = False

        # 重置重试计数器
        self.retry_count = 0

        for key, entry in self.thread_info.items():
            path, chunk_list = os.path.join(Config.Download.path, entry["file_name"]), entry["chunk_list"]

            if chunk_list[0] >= chunk_list[1]:
                continue

            # 重新下载前检查链接是否有效
            (durl, total_size) = self.get_total_size(entry["url"], entry["referer_url"]) 

            self.ThreadPool.submit(target = self.range_download, args = (key, durl, entry["referer_url"], path, chunk_list,))
            self.thread_alive_count += 1
        
        self.ThreadPool.start()

    def range_download(self, thread_id: str, url: str, referer_url: str, path: str, chunk_list: list):
        # 分片下载
        try:
            req = self.session.get(url, headers = get_header(referer_url, Config.User.sessdata, chunk_list), stream = True, proxies = get_proxy(), auth = get_auth(), timeout = 15)
            
            with open(path, "rb+") as f:
                start_time = time.time()
                chunk_size = 8192
                speed_limit = Config.Download.speed_limit_in_mb * 1024 * 1024
                f.seek(chunk_list[0])

                for chunk in req.iter_content(chunk_size = chunk_size):
                    if chunk:
                        if self.range_stop_flag:
                            # 检测分片下载停止标志位
                            break

                        f.write(chunk)
                        f.flush()

                        self.completed_size += len(chunk)

                        self.thread_info[thread_id]["chunk_list"][0] += len(chunk)

                        if self.completed_size >= self.total_size:
                            # 下载完成，置停止分片下载标志位为 True，下载完成标志位为 True
                            self.range_stop_flag = True
                            self.finish_flag = True

                        # 计算执行时间
                        elapsed_time = time.time() - start_time
                        expected_time = chunk_size / (speed_limit / self.thread_alive_count)

                        if elapsed_time < 1 and Config.Download.speed_limit:
                            # 计算应暂停的时间，从而限制下载速度
                            time.sleep(max(0, expected_time - elapsed_time))

                        start_time = time.time()

        except Exception:
            # 置错误标志位为 True
            self.error_flag = True

            # 抛出异常，停止线程
            raise requests.exceptions.ConnectionError()
        
        self.thread_alive_count -= 1

    def onListen(self):
        # 监听线程，负责监听下载进度
        while not self.stop_flag:
            temp_size = self.completed_size

            time.sleep(1)
            
            # 记录下载信息
            speed = self.format_speed((self.completed_size - temp_size) / 1024)

            info = {
                "progress": int(self.completed_size / self.total_size * 100),
                "speed": speed,
                "size": "{}/{}".format(format_size(self.completed_size / 1024), format_size(self.total_size / 1024)),
                "complete": format_size(self.completed_size / 1024),
                "raw_completed_size": self.completed_size
            }

            if speed == "0 KB/s":
                self.retry_count += 1

            if self.retry_count == 5:
                self.onStop()

                self.restart()

            if self.stop_flag:
                # 检测停止标志位
                break

            if self.error_flag:
                # 检测错误标志位，回调下载失败函数
                self.onError()
                break

            if self.finish_flag:
                # 检测下载完成标志位
                self.stop_flag = True
                self.onFinished()
                break
            
            self.update_download_info()

            wx.CallAfter(self.onDownload, info)

    def onPause(self):
        # 暂停下载
        self.onStop()

        self.update_download_info()

    def onResume(self):
        # 恢复下载
        self.restart()

        # 启动监听线程
        self.listen_thread = Thread(target = self.onListen, name = "ListenThread")

        self.listen_thread.start()

    def onStop(self):
        # 停止下载
        self.range_stop_flag = True
        self.stop_flag = True

        self.ThreadPool.stop()

    def onFinished(self):
        # 下载完成，关闭所有线程，回调 onMerge 进行合成
        self.stop_flag = True

        wx.CallAfter(self.onMerge)
    
    def onError(self):
        # 关闭线程池和监听线程，停止下载
        self.onStop()

        # 回调 panel 下载失败函数，终止下载
        wx.CallAfter(self.onErrorEx)
    
    def get_total_size(self, url_list: list, referer_url: str, path: Optional[str] = None):
        for url in url_list:
            headers = self.get_header_info(url, referer_url)

            # 检测 headers 是否包含 Content-Length，不包含的链接属于无效链接
            if "Content-Length" not in headers:
                # 无效链接，遍历下一个
                continue

            total_size = int(headers["Content-Length"])

            break

        # 当 path 不为空时，才创建本地空文件
        if path:
            with open(path, "wb") as f:
                # 使用 seek 方法，移动文件指针，快速有效，完美解决大文件创建耗时的问题
                f.seek(total_size - 1)
                f.write(b"\0")
        
        # 返回可以正常下载的链接
        return (url, total_size)
    
    def get_header_info(self, url: str, referer_url: str):
        # 获取链接 headers 信息
        req = self.session.head(url, headers = get_header(referer_url))

        return req.headers

    def get_chunk_list(self, total_size: int, chunk: int) -> list:
        # 计算分片下载区间
        piece_size = int(total_size / chunk)
        chunk_list = []

        for i in range(chunk):
            start = i * piece_size + 1 if i != 0 else 0 
            end = (i + 1) * piece_size if i != chunk - 1 else total_size

            chunk_list.append([start, end])

        return chunk_list

    def format_speed(self, speed: int) -> str:
        return "{:.1f} MB/s".format(speed / 1024) if speed > 1024 else "{:.1f} KB/s".format(speed) if speed > 0 else "0 KB/s"
    
    def update_download_info(self):
        self.download_info.update_thread_info(self.thread_info, self.completed_size)

    def update_total_size(self, total_size):
        self.download_info.update_base_info_total_size(total_size)

class DownloaderInfo:
    def __init__(self):
        # 下载信息类，用于断点续传
        self.path = os.path.join(os.getcwd(), "download.json")
    
    def check_file(self):
        if not os.path.exists(self.path):
            contents = {}

            self.write(contents)

    def read_info(self):
        self.check_file()
        
        with open(self.path, "r", encoding = "utf-8") as f:
            try:
                return json.loads(f.read())
            
            except Exception:
                return {}
    
    def init_info(self, info):
        self.id = info["id"]
        contents = self.read_info()

        contents[str(info["id"])] = {
                "base_info": info,
                "thread_info": {}
            }
        
        self.write(contents)
        
    def update_thread_info(self, thread_info, completed_size):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["thread_info"] = thread_info
            contents[f"{self.id}"]["base_info"]["completed_size"] = completed_size

            self.write(contents)

    def update_base_info(self, base_info):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["base_info"]["size"] = base_info["size"]
            contents[f"{self.id}"]["base_info"]["video_codec"] = base_info["video_codec"]
            contents[f"{self.id}"]["base_info"]["complete"] = base_info["complete"]
            contents[f"{self.id}"]["base_info"]["video_quality"] = base_info["video_quality"]
            
            self.write(contents)

    def update_base_info_progress(self, progress, complete):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["base_info"]["progress"] = progress
            contents[f"{self.id}"]["base_info"]["complete"] = complete

            self.write(contents)

    def update_base_info_status(self, status):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["base_info"]["status"] = status

            self.write(contents)

    def update_base_info_total_size(self, total_size):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["base_info"]["total_size"] = total_size

            self.write(contents)

    def update_base_info_download_complete(self, status: bool):
        contents = self.read_info()

        if f"{self.id}" in contents:
            contents[f"{self.id}"]["base_info"]["download_complete"] = status

            self.write(contents)

    def write(self, contents):
        with open(self.path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False))
    
    def clear(self):
        contents = self.read_info()

        id_string = str(self.id)

        if id_string in contents:
            contents.pop(id_string)

        self.write(contents)
    
    def calc_completed_size(self, total_size, thread_info):
        uncompleted_size = 0

        for key, thread_entry in thread_info.items():
            chunk_list = thread_entry["chunk_list"]

            if chunk_list[0] < chunk_list[1]:
                uncompleted_size += chunk_list[1] - chunk_list[0]
        
        return total_size - uncompleted_size