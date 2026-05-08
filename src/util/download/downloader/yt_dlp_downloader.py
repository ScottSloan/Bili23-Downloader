from yt_dlp import YoutubeDL
import os
import threading
import logging
from pathlib import Path

from util.common.enum import DownloadStatus

logger = logging.getLogger(__name__)

# JavaScript 运行时和 FFmpeg 配置
# 使用项目目录下的工具
def get_bin_path(bin_name):
    """获取工具路径"""
    # 项目目录下的 bin 文件夹
    project_bin = Path(__file__).parent.parent.parent.parent.parent / "bin" / bin_name
    if project_bin.exists():
        return str(project_bin)
    
    # 系统 PATH 中的工具
    return bin_name

# 初始化 Node.js 运行时
_node_runtime = None

def get_node_runtime():
    """获取 Node.js 运行时实例"""
    global _node_runtime
    if _node_runtime is None:
        try:
            from util.runtime.node_runtime import NodeRuntime
            _node_runtime = NodeRuntime()
            # 将 Node.js 目录添加到 PATH
            _node_runtime.add_to_path()
            logger.info(f"Node.js 运行时初始化成功: {_node_runtime.node_path}")
        except Exception as e:
            logger.warning(f"Node.js 运行时初始化失败: {e}")
            _node_runtime = None
    return _node_runtime

def get_node_exe():
    """获取 Node.js 可执行文件路径"""
    runtime = get_node_runtime()
    if runtime and runtime.exists():
        return str(runtime.node_path)
    # 如果 NodeRuntime 不可用，回退到直接查找
    return get_bin_path("node.exe")

FFMPEG_DIR = str(Path(get_bin_path("ffmpeg.exe")).parent) if os.path.exists(get_bin_path("ffmpeg.exe")) else None


class YTDLPDownloader:
    """
    通用下载引擎（B站 / YouTube / 全网站）
    """

    def __init__(self):
        self.progress_callback = None
        self.finish_callback = None
        self.error_callback = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始状态为非暂停
        self._ydl = None
        self._is_downloading = False
        self._task_info = None
        self._download_thread = None

    def set_callbacks(self, progress=None, finish=None, error=None):
        self.progress_callback = progress
        self.finish_callback = finish
        self.error_callback = error

    def set_task_info(self, task_info):
        """设置任务信息，用于获取 cookie_file 等配置"""
        self._task_info = task_info

    def start(self):
        """开始下载"""
        if not self._task_info:
            logger.error("任务信息未设置，无法开始下载")
            return

        if self._is_downloading:
            logger.warning("下载已在进行中")
            return

        # 重置状态
        self._stop_event.clear()
        self._pause_event.set()

        # 更新任务状态为下载中
        self._task_info.Download.status = DownloadStatus.DOWNLOADING

        logger.info(f"任务 cookie_file: {self._task_info.cookie_file}")
        
        cookie_file = None
        if self._task_info.cookie_file:
            if os.path.exists(self._task_info.cookie_file):
                if self._validate_cookie_file(self._task_info.cookie_file):
                    cookie_file = self._task_info.cookie_file
                    logger.info(f"使用 cookie 文件: {cookie_file}")
                else:
                    logger.warning(f"Cookie 文件验证失败: {self._task_info.cookie_file}")
                    if self.error_callback:
                        self.error_callback(f"Cookie 文件格式错误或无效: {self._task_info.cookie_file}")
            else:
                logger.warning(f"Cookie 文件不存在: {self._task_info.cookie_file}")
                if self.error_callback:
                    self.error_callback(f"Cookie 文件不存在: {self._task_info.cookie_file}")
        else:
            logger.warning("任务未设置 cookie_file")

        self._is_downloading = True
        self._stop_event.clear()
        self._pause_event.set()

        self._download_thread = threading.Thread(
            target=self.download,
            args=(self._task_info.Episode.url, self._task_info.File.download_path, cookie_file),
            daemon=True
        )
        self._download_thread.start()

    def pause(self):
        """暂停下载"""
        if not self._is_downloading:
            logger.warning("下载未开始，无法暂停")
            return
        
        self._pause_event.clear()  # 清除事件，阻塞下载
        self._is_downloading = False
        
        # 更新任务状态为已暂停
        if self._task_info:
            self._task_info.Download.status = DownloadStatus.PAUSED
        
        logger.info("下载已暂停")

    def resume(self):
        """继续下载"""
        if self._is_downloading:
            logger.warning("下载已在进行中，无法继续")
            return
        
        self._pause_event.set()  # 设置事件，允许下载
        self._is_downloading = True
        
        # 更新任务状态为下载中
        if self._task_info:
            self._task_info.Download.status = DownloadStatus.DOWNLOADING
        
        # 重新开始下载
        if self._task_info:
            cookie_file = None
            if self._task_info.cookie_file and os.path.exists(self._task_info.cookie_file):
                cookie_file = self._task_info.cookie_file

            self._download_thread = threading.Thread(
                target=self.download,
                args=(self._task_info.Episode.url, self._task_info.File.download_path, cookie_file),
                daemon=True
            )
            self._download_thread.start()
            logger.info("下载已继续")

    def retry(self):
        """重试下载"""
        self._stop_event.clear()
        self._pause_event.set()
        self.start()
        logger.info("重试下载")

    def start_merge(self):
        """开始合并"""
        pass

    def download(self, url, output_dir="downloads", cookie_file=None):
        """
        主下载入口
        """
        from util.common import config
        from util.network.proxy import Proxy
        
        ydl_opts = {
            # 画质策略（通用）
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",

            # 输出路径
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",

            # 进度回调
            "progress_hooks": [self._hook],

            # 后处理回调，用于获取最终文件名
            "postprocessor_hooks": [self._postprocessor_hook],

            # 稳定性 - 增加重试次数以应对代理连接问题
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,

            # 日志控制 - 调试模式
            "quiet": False,
            "no_warnings": False,
            "verbose": True,
            
            # JavaScript 运行时配置 - 使用 Node.js 解决 YouTube 反机器人挑战
            "js_runtimes": {"node": {"path": get_node_exe()}},
            
            # 启用远程组件下载 - 解决 YouTube JS 挑战
            "remote_components": ["ejs:github"],
            
            # SSL 配置 - 解决 SSL 连接问题
            "nocheckcertificate": True,  # 跳过 SSL 证书验证（仅用于解决连接问题）
            
            # 请求处理器配置 - 使用 curl_cffi 解决 SSL 问题
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "android", "ios", "web_embedded", "web_music", "web_safari", "tv_embedded"],
                    "player_skip": ["webpage"],
                }
            },
        }
        
        # FFmpeg 配置
        if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
            ydl_opts["ffmpeg_location"] = FFMPEG_DIR
            logger.info(f"使用 FFmpeg 目录: {FFMPEG_DIR}")
        
        # 代理配置
        proxy = Proxy()
        if proxy.enabled:
            proxies = proxy.get_proxies()
            if proxies:
                proxy_url = proxies.get("http") or proxies.get("https")
                if proxy_url:
                    ydl_opts["proxy"] = proxy_url
                    logger.info(f"使用代理: {proxy_url}")

        # cookie（B站/YouTube premium）
        logger.info(f"download() 收到 cookie_file: {cookie_file}")
        
        # 针对 YouTube 的特殊处理
        if "youtube.com" in url or "youtu.be" in url:
            ydl_opts["extract_flat"] = False
            ydl_opts["ignoreerrors"] = False
            
            # 优先使用用户手动选择的 cookies 文件
            if cookie_file:
                logger.info(f"开始验证 cookie 文件: {cookie_file}")
                if self._validate_cookie_file(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
                    logger.info(f"使用用户选择的 cookie 文件: {cookie_file}")
                else:
                    logger.warning(f"Cookie 文件验证失败，尝试从浏览器获取 cookies: {cookie_file}")
                    # 如果用户选择的文件无效，尝试从浏览器获取
                    browser_cookies = self._get_browser_cookies_for_youtube()
                    if browser_cookies:
                        ydl_opts["cookiesfrombrowser"] = browser_cookies
                        logger.info(f"使用浏览器 cookies: {browser_cookies}")
                    else:
                        logger.warning("无法从浏览器获取 cookies")
                        if self.error_callback:
                            self.error_callback(f"Cookie 文件格式错误或无效，且无法从浏览器获取 cookies。请确保使用 Netscape 格式的 cookies 文件，或确保浏览器已登录 YouTube。")
            else:
                # 用户未选择 cookies 文件，尝试从浏览器获取
                browser_cookies = self._get_browser_cookies_for_youtube()
                if browser_cookies:
                    ydl_opts["cookiesfrombrowser"] = browser_cookies
                    logger.info(f"使用浏览器 cookies: {browser_cookies}")
                else:
                    logger.warning("未提供 cookie_file 参数，且无法从浏览器获取 cookies")
                    if self.error_callback:
                        self.error_callback("未配置 cookies，YouTube 下载可能需要登录认证。请在解析界面选择 cookies 文件或确保浏览器已登录 YouTube。")
            
            # 添加 YouTube 特定的配置
            ydl_opts.update(self._get_youtube_specific_opts())
        elif cookie_file:
            # 非 YouTube 网站使用文件 cookies
            logger.info(f"开始验证 cookie 文件: {cookie_file}")
            if self._validate_cookie_file(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
                logger.info(f"使用 cookie 文件: {cookie_file}")
            else:
                logger.warning(f"Cookie 文件验证失败，将不使用 cookies: {cookie_file}")
        else:
            logger.info("未提供 cookie_file 参数")

        self._is_downloading = True
        self._stop_event.clear()
        self._pause_event.set()

        try:
            with YoutubeDL(ydl_opts) as ydl:
                self._ydl = ydl
                ydl.download([url])

            if self.finish_callback and not self._stop_event.is_set():
                self.finish_callback(url)

        except Exception as e:
            error_msg = str(e)
            
            # 如果是 YouTube 认证错误，尝试使用浏览器 cookies 重试
            if ("Sign in to confirm" in error_msg or "LOGIN_REQUIRED" in error_msg) and "youtube.com" in url:
                logger.warning("Cookies 认证失败，尝试使用浏览器 cookies 重试...")
                
                # 尝试从浏览器获取 cookies
                browser_cookies = self._get_browser_cookies_for_youtube()
                if browser_cookies:
                    logger.info(f"使用浏览器 cookies 重试: {browser_cookies}")
                    ydl_opts["cookiesfrombrowser"] = browser_cookies
                    # 移除可能无效的文件 cookies
                    if "cookiefile" in ydl_opts:
                        del ydl_opts["cookiefile"]
                    
                    try:
                        with YoutubeDL(ydl_opts) as ydl:
                            self._ydl = ydl
                            ydl.download([url])
                        
                        if self.finish_callback and not self._stop_event.is_set():
                            self.finish_callback(url)
                        return  # 重试成功，直接返回
                    except Exception as retry_e:
                        logger.error(f"使用浏览器 cookies 重试失败: {retry_e}")
                        if self.error_callback:
                            self.error_callback(f"下载失败: {retry_e}")
                        return
            
            if self._stop_event.is_set():
                logger.info("下载被用户停止")
            elif "Download stopped by user" in error_msg:
                logger.info("下载被用户停止")
            elif self.error_callback:
                logger.error(f"下载失败: {error_msg}")
                self.error_callback(error_msg)
            else:
                logger.error(f"下载失败: {error_msg}")
        finally:
            self._is_downloading = False
            self._ydl = None

    def _validate_cookie_file(self, cookie_file):
        """
        验证 cookie 文件的有效性
        
        Args:
            cookie_file: cookie 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            if not os.path.exists(cookie_file):
                logger.warning(f"Cookie 文件不存在: {cookie_file}")
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(cookie_file)
            if file_size == 0:
                logger.warning(f"Cookie 文件为空: {cookie_file}")
                return False
            
            # 检查文件内容格式
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # yt-dlp 需要 Netscape 格式的 cookies 文件
            # Netscape 格式检查（包含制表符分隔的字段）
            if '\t' in content:
                lines = content.split('\n')
                valid_lines = 0
                for line in lines:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        valid_lines += 1
                
                if valid_lines > 0:
                    logger.info(f"Cookie 文件格式正确 (Netscape): {cookie_file} ({valid_lines} 个 cookies)")
                    return True
            
            logger.warning(f"Cookie 文件格式错误，需要 Netscape 格式: {cookie_file}")
            return False
            
        except Exception as e:
            logger.error(f"验证 cookie 文件时出错: {e}")
            return False

    def _get_browser_cookies_for_youtube(self):
        """
        尝试从浏览器获取 YouTube cookies
        
        Returns:
            tuple: (browser_name,) 或 None
        """
        import platform
        import os
        
        # 检测可用的浏览器
        browsers_to_try = []
        
        if platform.system() == "Windows":
            # Windows 常见浏览器路径
            browsers = {
                "firefox": os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles"),
                "chrome": os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"),
                "edge": os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data"),
            }
            
            for browser, path in browsers.items():
                if os.path.exists(path):
                    browsers_to_try.append(browser)
        
        # 优先尝试 Firefox（测试成功）
        if "firefox" in browsers_to_try:
            logger.info("检测到 Firefox 浏览器，尝试使用其 cookies")
            try:
                from yt_dlp.cookies import extract_cookies_from_browser
                cookies = extract_cookies_from_browser('firefox')
                youtube_cookies = [c for c in cookies if 'youtube.com' in c.domain or '.youtube.com' == c.domain]
                if len(youtube_cookies) > 5:
                    logger.info(f"成功从 Firefox 提取 {len(youtube_cookies)} 个 YouTube cookies")
                    return ("firefox",)
                else:
                    logger.warning(f"Firefox cookies 数量不足 ({len(youtube_cookies)} 个)，可能浏览器未登录 YouTube")
            except Exception as e:
                logger.warning(f"从 Firefox 提取 cookies 失败: {e}")
        elif "chrome" in browsers_to_try:
            logger.info("检测到 Chrome 浏览器，尝试使用其 cookies")
            try:
                from yt_dlp.cookies import extract_cookies_from_browser
                cookies = extract_cookies_from_browser('chrome')
                youtube_cookies = [c for c in cookies if 'youtube.com' in c.domain or '.youtube.com' == c.domain]
                if len(youtube_cookies) > 5:
                    logger.info(f"成功从 Chrome 提取 {len(youtube_cookies)} 个 YouTube cookies")
                    return ("chrome",)
                else:
                    logger.warning(f"Chrome cookies 数量不足 ({len(youtube_cookies)} 个)，可能浏览器未登录 YouTube")
            except Exception as e:
                logger.warning(f"从 Chrome 提取 cookies 失败: {e}")
        elif "edge" in browsers_to_try:
            logger.info("检测到 Edge 浏览器，尝试使用其 cookies")
            try:
                from yt_dlp.cookies import extract_cookies_from_browser
                cookies = extract_cookies_from_browser('edge')
                youtube_cookies = [c for c in cookies if 'youtube.com' in c.domain or '.youtube.com' == c.domain]
                if len(youtube_cookies) > 5:
                    logger.info(f"成功从 Edge 提取 {len(youtube_cookies)} 个 YouTube cookies")
                    return ("edge",)
                else:
                    logger.warning(f"Edge cookies 数量不足 ({len(youtube_cookies)} 个)，可能浏览器未登录 YouTube")
            except Exception as e:
                logger.warning(f"从 Edge 提取 cookies 失败: {e}")
        
        logger.warning("未检测到支持的浏览器或提取失败")
        return None

    def _get_youtube_specific_opts(self):
        """
        获取 YouTube 特定的配置选项
        
        Returns:
            dict: YouTube 特定的配置选项
        """
        youtube_opts = {
            # YouTube 特定配置 - 使用 tv 和 android_vr 客户端，支持 cookies
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr", "tv"],
                    "player_skip": ["web", "mweb", "android", "ios"],
                }
            },
            # 更好的错误处理
            "ignoreerrors": False,
            "skip_unavailable_fragments": True,
            # 网络配置
            "forceipv4": True,
            "nocheckcertificate": True,
        }
        
        return youtube_opts

    def _postprocessor_hook(self, info):
        """
        yt-dlp 后处理回调，用于获取最终文件名
        """
        if info.get("status") == "finished" and self._task_info:
            # 获取最终文件名
            final_filename = info.get("filename", "")
            if final_filename:
                from pathlib import Path
                final_basename = Path(final_filename).name
                
                # 更新 relative_files，添加最终文件并移除临时文件
                if final_basename not in self._task_info.File.relative_files:
                    self._task_info.File.relative_files.append(final_basename)
                
                # 移除临时文件（video_xxx.m4s 和 audio_xxx.m4a）
                temp_files = [f for f in self._task_info.File.relative_files 
                             if f.startswith("video_") or f.startswith("audio_")]
                for temp_file in temp_files:
                    self._task_info.File.relative_files.remove(temp_file)
                
                logger.info(f"最终文件: {final_basename}")

    def _hook(self, d):
        """
        yt-dlp 进度回调
        """
        # 下载完成时直接处理，不需要等待暂停事件
        if d["status"] == "finished":
            if self.progress_callback:
                self.progress_callback({
                    "status": "finished",
                    "filename": d.get("filename"),
                })
            return

        # 检查是否需要暂停
        if not self._pause_event.is_set():
            self._pause_event.wait()  # 阻塞直到继续

        if self._stop_event.is_set():
            raise Exception("Download stopped by user")

        if d["status"] == "downloading":
            if self.progress_callback:
                self.progress_callback({
                    "status": "downloading",
                    "filename": d.get("filename"),
                    "percent": d.get("_percent_str", "").strip(),
                    "speed": d.get("_speed", 0),
                    "speed_str": d.get("_speed_str", "").strip(),
                    "eta": d.get("_eta_str", "").strip(),
                })
