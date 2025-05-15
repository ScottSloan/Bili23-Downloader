class AudioInfo:
    class Availability:
        audio: bool = False

        hires: bool = False
        dolby: bool = False
        _192K: bool = False
        _132K: bool = False
        _64K: bool = False

    download_audio_only: int = False

    audio_quality_id: int = 0

    audio_quality_id_list = []
    audio_quality_desc_list = []

    @classmethod
    def get_audio_quality_list(cls, json_dash: dict):
        def get_audio_availability():
            # 检测 Hi-Res 无损是否可用
            if "flac" in json_dash:
                if json_dash["flac"]:
                    cls.Availability.hires = True

            # 检测杜比全景声是否可用
            if "dolby" in json_dash:
                if "audio" in json_dash["dolby"]:
                    if json_dash["dolby"]["audio"]:
                        cls.Availability.dolby = True

            # 检测 192k, 132k, 64k 音质是否存在
            if "audio" in json_dash:
                if json_dash["audio"]:
                    for entry in json_dash["audio"]:
                        match entry["id"]:
                            case 30280:
                                cls.Availability._192K = True

                            case 30232:
                                cls.Availability._132K = True

                            case 30216:
                                cls.Availability._64K = True
            
                    cls.Availability.audio = True
            else:
                cls.Availability.audio = False
        
        def get_list():
            if cls.Availability.hires:
                cls.audio_quality_id_list.append(30251)
                cls.audio_quality_desc_list.append("Hi-Res 无损")

            if cls.Availability.dolby:
                cls.audio_quality_id_list.append(30250)
                cls.audio_quality_desc_list.append("杜比全景声")

            if cls.Availability._192K:
                cls.audio_quality_id_list.append(30280)
                cls.audio_quality_desc_list.append("192K")

            if cls.Availability._132K:
                cls.audio_quality_id_list.append(30232)
                cls.audio_quality_desc_list.append("132K")

            if cls.Availability._64K:
                cls.audio_quality_id_list.append(30216)
                cls.audio_quality_desc_list.append("64K")

        from utils.config import Config

        get_audio_availability()

        get_list()

        cls.audio_quality_id = Config.Download.audio_quality_id

    @classmethod
    def clear_audio_info(cls):
        cls.Availability.audio = False
        cls.Availability.hires = False
        cls.Availability.dolby = False
        cls.Availability._192K = False
        cls.Availability._132K = False
        cls.Availability._64K = False

        cls.audio_quality_id = 0

        cls.audio_quality_id_list.clear()
        cls.audio_quality_desc_list.clear()
