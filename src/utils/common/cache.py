from typing import Any

class DataCache:
    cache_dict = {}

    @staticmethod
    def get_cache(key: str):
        if key in DataCache.cache_dict:
            return DataCache.cache_dict.get(key)
        
    @staticmethod
    def set_cache(key: str, value: Any):
        DataCache.cache_dict[key] = value

    @staticmethod
    def clear_cache():
        DataCache.cache_dict.clear()