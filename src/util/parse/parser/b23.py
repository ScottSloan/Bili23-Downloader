from util.network.request import NetworkRequestWorker, ResponseType
from util.thread import SyncTask

class B23Parser:
    def __init__(self, url: str):
        self.url = url
        self.error_message = ""
    
    def redirect(self) -> str:
        def on_success(response: str):
            nonlocal redirect_url

            redirect_url = response

        def on_error(error: str):
            self.error_message = error

        redirect_url = ""

        worker = NetworkRequestWorker(self.url, response_type = ResponseType.REDIRECT_URL)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        SyncTask.run(worker)

        if redirect_url == self.url:
            self.on_error("b23.tv 短链已过期")

        if self.error_message:
            self.on_error(self.error_message)

        return redirect_url
    
    def on_error(self, error: str):
        raise Exception(error)
