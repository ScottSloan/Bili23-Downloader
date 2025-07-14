from utils.config import Config

from utils.common.map import audio_quality_map, audio_quality_sort_map, get_mapping_key_by_value
from utils.common.enums import AudioQualityID

class AudioInfo:
    audio: bool = False

    audio_quality_id: int = 0

    audio_quality_id_list: list = []
    audio_quality_desc_list: list = []

    @classmethod
    def get_all_audio_url_list(cls, data: dict):
        all_url_list = []
        
        audio_node = data.get("audio")
        dolby_node = data.get("dolby", {"audio": None})
        flac_node = data.get("flac", {"audio": None})

        dolby_node = dolby_node["audio"] if dolby_node else None
        flac_node = flac_node["audio"] if flac_node else None

        if audio_node:
            if isinstance(audio_node, list):
                all_url_list.extend(audio_node)

        if dolby_node:
            if isinstance(dolby_node, list):
                all_url_list.extend(dolby_node)
            else:
                all_url_list.append(dolby_node)

        if flac_node:
            if isinstance(flac_node, list):
                all_url_list.extend(flac_node)
            else:
                all_url_list.append(flac_node)

        all_url_list.sort(key = lambda x: audio_quality_sort_map.get(x["id"]))

        return all_url_list

    @classmethod
    def get_audio_quality_list(cls, json_dash: dict):
        audio_quality_id_list, audio_quality_desc_list = cls.get_audio_quality_id_desc_list(json_dash)

        cls.audio_quality_id_list = audio_quality_id_list.copy()
        cls.audio_quality_desc_list = audio_quality_desc_list.copy()

        cls.audio_quality_id = Config.Download.audio_quality_id

        cls.audio = len(cls.audio_quality_id_list) != 1

    @classmethod
    def get_audio_quality_id_desc_list(cls, json_dash: dict):
        audio_quality_id_list, audio_quality_desc_list = [AudioQualityID._Auto.value], ["自动"]

        all_url_list = cls.get_all_audio_url_list(json_dash)

        for entry in all_url_list:
            id = entry["id"]
            desc = get_mapping_key_by_value(audio_quality_map, id)

            if desc:
                audio_quality_id_list.append(id)
                audio_quality_desc_list.append(desc)

        return audio_quality_id_list, audio_quality_desc_list

    @classmethod
    def clear_audio_info(cls):
        cls.audio_quality_id = 0

        cls.audio_quality_id_list.clear()
        cls.audio_quality_desc_list.clear()
