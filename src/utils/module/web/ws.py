import json
import asyncio
import websockets
from websockets.server import ServerProtocol

from utils.config import Config

from utils.auth.login_v2 import LoginInfo

from utils.common.thread import Thread

class WebSocketServer:
    def __init__(self):
        self.server = None
        self.server_task = None
        self.loop = asyncio.new_event_loop()
        self.clients = set()

    async def handler(self, websocket: ServerProtocol):
        self.clients.add(websocket)

        try:
            async for message in websocket:
                await self.process_message(str(message))
        finally:
            self.clients.remove(websocket)

    async def process_message(self, message: str):
        async def queryCaptchaInfo():
            data = {
                "msg": "queryCaptchaInfo",
                "data": {
                    "gt": LoginInfo.Captcha.gt,
                    "challenge": LoginInfo.Captcha.challenge
                }
            }

            await self.broadcast(data)

        async def captchaResult():
            LoginInfo.Captcha.seccode = data["data"]["seccode"]
            LoginInfo.Captcha.validate = data["data"]["validate"]

            LoginInfo.Captcha.flag = False

            self.stop()

        data = json.loads(message)

        print(data)

        match data.get("msg"):
            case "queryCaptchaInfo":
                await queryCaptchaInfo()

            case "captchaResult":
                await captchaResult()

    async def broadcast(self, data: dict):
        message = json.dumps(data, ensure_ascii = False)

        if self.clients:
            await asyncio.gather(
                *(client.send(message) for client in self.clients)
            )

    def start(self):
        async def run():
            self.server = await websockets.serve(self.handler, "localhost", port = Config.Advanced.websocket_port)

            await self.server.wait_closed()

        self.server_task = self.loop.create_task(run())

        Thread(target = self.loop.run_forever).start()

    def stop(self):
        if self.server:
            self.loop.call_soon_threadsafe(self.server_task.cancel)
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.server = None

    @classmethod
    def running(cls):
        return cls.server is not None