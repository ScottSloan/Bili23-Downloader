
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
    aduio_quality_desc_list = []

    @staticmethod
    def get_audio_quality_list(json_dash: dict):
        def _get_audio_availability():
            # 检测 Hi-Res 无损是否可用
            if "flac" in json_dash:
                if json_dash["flac"]:
                    AudioInfo.Availability.hires = True

            # 检测杜比全景声是否可用
            if "dolby" in json_dash:
                if "audio" in json_dash["dolby"]:
                    if json_dash["dolby"]["audio"]:
                        AudioInfo.Availability.dolby = True

            # 检测 192k, 132k, 64k 音质是否存在
            if "audio" in json_dash:
                if json_dash["audio"]:
                    for entry in json_dash["audio"]:
                        match entry["id"]:
                            case 30280:
                                AudioInfo.Availability._192K = True

                            case 30232:
                                AudioInfo.Availability._132K = True

                            case 30216:
                                AudioInfo.Availability._64K = True
            
                AudioInfo.Availability.audio = True
            else:
                AudioInfo.Availability.audio = False
        
        def _get_list():
            if AudioInfo.Availability.hires:
                AudioInfo.audio_quality_id_list.append(30251)
                AudioInfo.aduio_quality_desc_list.append("Hi-Res 无损")

            if AudioInfo.Availability.dolby:
                AudioInfo.audio_quality_id_list.append(30250)
                AudioInfo.aduio_quality_desc_list.append("杜比全景声")

            if AudioInfo.Availability._192K:
                AudioInfo.audio_quality_id_list.append(30280)
                AudioInfo.aduio_quality_desc_list.append("192K")

            if AudioInfo.Availability._132K:
                AudioInfo.audio_quality_id_list.append(30232)
                AudioInfo.aduio_quality_desc_list.append("132K")

            if AudioInfo.Availability._64K:
                AudioInfo.audio_quality_id_list.append(30216)
                AudioInfo.aduio_quality_desc_list.append("64K")

        from utils.config import Config

        _get_audio_availability()

        _get_list()

        AudioInfo.audio_quality_id = Config.Download.audio_quality_id

    @staticmethod
    def clear_audio_info():
        AudioInfo.Availability.audio = AudioInfo.Availability.hires = AudioInfo.Availability.dolby = AudioInfo.Availability._192K = AudioInfo.Availability._132K = AudioInfo.Availability._64K = False
        AudioInfo.audio_quality_id = 0

        AudioInfo.audio_quality_id_list.clear()
        AudioInfo.aduio_quality_desc_list.clear()
