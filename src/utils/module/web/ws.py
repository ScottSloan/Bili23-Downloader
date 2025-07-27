import asyncio
import websockets
from websockets.server import ServerProtocol

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
                print(message)
        finally:
            self.clients.remove(websocket)

    def start(self):
        async def run():
            self.server = await websockets.serve(self.handler, "localhost", port = 8765)

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