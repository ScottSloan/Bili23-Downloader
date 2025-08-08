from utils.common.request import RequestUtils

class Recorder:
    def __init__(self):
        pass

    def record_thread(self):
        file = ""

        with open(file, "r+b") as f:
            with RequestUtils.request_get("", stream = True) as req:
                for chunk in req.iter_content(chunk_size = 1024):
                    if chunk:
                        f.write(chunk)
