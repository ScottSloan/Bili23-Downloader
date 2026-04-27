from util.network import SyncNetWorkRequest, ResponseType

class B23Parser:
    def __init__(self):
        pass
    
    def parse(self, url: str) -> str:
        self.url = url
        
        request = SyncNetWorkRequest(self.url, response_type = ResponseType.REDIRECT_URL)
        response = request.run()

        if response == self.url:
            self.on_error("b23.tv 短链已过期")

        return response
    
    def on_error(self, error: str):
        raise Exception(error)
