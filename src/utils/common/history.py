import json

from utils.config import Config
from utils.common.datetime_util import DateTime

class History:
    def __init__(self):
        self.history_json: list[dict[str, str]] = []

        self.load()

    def add(self, url: str, title: str, category: str):
        def find():
            for entry in self.history_json:
                if entry.get("url") == url:
                    entry["time"] = DateTime.get_timestamp()

                    self.history_json.remove(entry)

                    return entry

        if not Config.Basic.enable_history:
            return
        
        if not (entry := find()):
            entry = {
                "time": DateTime.get_timestamp(),
                "url": url,
                "title": title,
                "category": category
            }
        
        self.history_json.append(entry)

        self.save()

    def clear(self):
        self.history_json.clear()

        self.save()

    def get(self):
        return self.history_json

    def get_json_data(self):
        json_data = {
            "history": self.history_json
        }

        return json.dumps(json_data, ensure_ascii = False, indent = 4)

    def save(self):
        with open(Config.APP.history_file_path, "w", encoding = "utf-8") as f:
            f.write(self.get_json_data())

    def load(self):
        try:
            with open(Config.APP.history_file_path, "r", encoding = "utf-8") as f:
                json_data = json.load(f)

            self.history_json = json_data.get("history", [])

        except Exception:
            self.save()