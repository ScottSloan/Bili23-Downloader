class ParserBase:
    def __init__(self):
        self.success_callback = None
        self.error_callback = None

    def enc_wbi(self, params: dict) -> str:
        return "&".join(f"{k}={v}" for k, v in params.items())

    def check_response(self, response: dict):
        if not response:
            if self.error_callback:
                self.error_callback("Empty response")
