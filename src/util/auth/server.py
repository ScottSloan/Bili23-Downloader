from PySide6.QtCore import QThread

from util.common import signal_bus

from .captcha import CaptchaInfo

from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process, Queue, Event
from urllib.parse import urlparse
from threading import Thread
import queue
import json

def run_server(host, port, req_queue, res_queue, stop_event):
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            parsed_url = urlparse(self.path)

            if parsed_url.path == "/geetest/captcha/init":
                # 请求主进程获取最新的 CaptchaInfo
                req_queue.put({"action": "get_geetest_info"})
                
                # 阻塞等待主进程响应
                while not stop_event.is_set():
                    try:
                        msg = res_queue.get(timeout=0.1)
                        if msg.get("action") == "geetest_info":
                            data = {
                                "challenge": msg["challenge"],
                                "gt": msg["gt"],
                            }
                            self.make_response(200, json.dumps(data), is_json=True)
                            break
                    except queue.Empty:
                        continue
            else:
                self.make_response(404, "Not Found")

        def do_POST(self):
            parsed_url = urlparse(self.path)

            if parsed_url.path == "/geetest/captcha/callback":
                content_length = int(self.headers.get("Content-Length", 0))
                
                if self.headers.get("Content-Type") == "application/json;charset=UTF-8":
                    post_data = self.rfile.read(content_length).decode("utf-8")
                    json_data = json.loads(post_data)

                    # 发送回主进程保存，并触发信号
                    req_queue.put({
                        "action": "captcha_success",
                        "seccode": json_data["seccode"],
                        "validate": json_data["validate"]
                    })

                self.make_response(200, "OK")
            else:
                self.make_response(404, "Not Found")

        def make_response(self, code: int, content: str, is_json: bool = False):
            self.send_response(code)
            self.send_header("Content-Type", "application/json" if is_json else "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = HTTPServer((host, port), CallbackHandler)
    server.timeout = 0.5  # 使得 handle_request 不会无限阻塞
    
    while not stop_event.is_set():
        server.handle_request()
        
    server.server_close()

class QueueListenerThread(QThread):
    def __init__(self, req_queue, res_queue):
        super().__init__()
        self.req_queue = req_queue
        self.res_queue = res_queue
        self.running = True

    def run(self):
        while self.running:
            try:
                msg = self.req_queue.get(timeout=0.1)
                action = msg.get("action")
                
                if action == "get_geetest_info":
                    self.res_queue.put({
                        "action": "geetest_info",
                        "challenge": CaptchaInfo.challenge,
                        "gt": CaptchaInfo.gt
                    })
                elif action == "captcha_success":
                    CaptchaInfo.seccode = msg["seccode"]
                    CaptchaInfo.validate = msg["validate"]
                    # 安全地在主进程触发 Qt 信号
                    signal_bus.login.send_sms.emit()
            except queue.Empty:
                pass

    def stop(self):
        self.running = False
        self.wait()

class ServerManager:
    def __init__(self, host="127.0.0.1", port=2333):
        self.host = host
        self.port = port
        
        self.process = None
        self.req_queue = None
        self.res_queue = None
        self.stop_event = None
        self.listener_thread = None
        self.running = False

        signal_bus.login.start_server.connect(self.start)
        signal_bus.login.stop_server.connect(self.stop)

    def start(self):
        if not self.running:
            self.req_queue = Queue()
            self.res_queue = Queue()
            self.stop_event = Event()

            # 启动监听线程
            self.listener_thread = QueueListenerThread(self.req_queue, self.res_queue)
            self.listener_thread.start()

            # 启动控制台子进程
            self.process = Process(
                target=run_server, 
                args=(self.host, self.port, self.req_queue, self.res_queue, self.stop_event), 
                daemon=True
            )
            self.process.start()
            
            self.running = True

    def stop(self):
        if self.running:
            self.stop_event.set()
            self.running = False

            process = self.process
            listener_thread = self.listener_thread

            self.process = None
            self.req_queue = None
            self.res_queue = None
            self.stop_event = None
            self.listener_thread = None

            def cleanup():
                if listener_thread:
                    listener_thread.stop()

                if process:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout = 1.0)

            Thread(target = cleanup, daemon = True).start()

server_manager = ServerManager()
