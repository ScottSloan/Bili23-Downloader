from dataclasses import dataclass, field, fields, asdict

@dataclass
class InfoBase:
    def from_dict(self, data: dict) -> None:
        field_names = {f.name for f in fields(self)}

        for k, v in data.items():
            if k in field_names:
                setattr(self, k, v)

@dataclass
class BasicInfo(InfoBase):
    task_id: str = ""
    cover_id: str = ""
    show_title: str = ""
    created_time: int = 0
    completed_time: int = 0

@dataclass
class FileInfo(InfoBase):
    name: str = ""
    
    download_path: str = ""
    folder: str = ""

    video_file_ext: str = ""
    audio_file_ext: str = ""
    merge_file_ext: str = ""

    relative_files: list[str] = field(default_factory = list)

@dataclass
class EpisodeInfo(InfoBase):
    attribute: int = 0

    aid: int = 0
    bvid: str = ""
    cid: int = 0
    cover: str = ""
    ep_id: int = 0
    pubtime: int = 0
    number: str = ""
    part_number: int = 0
    episode_number: int = 0

    leaf_title: str = ""
    parent_title: str = ""
    section_title: str = ""
    collection_title: str = ""
    series_title: str = ""
    season_title: str = ""
    episode_title: str = ""

    areas: list[str] = field(default_factory = list)
    actors: str = ""
    description: str = ""
    episode_plot: str = ""
    uploader: str = ""
    uploader_uid: int = 0
    premiered: int = 0
    poster: str = ""
    season_id: int = 0
    season_number: int = 0
    styles: list[str] = field(default_factory = list)
    rating: float = 0.0
    tid: int = 0
    tid_v2: int = 0
    url: str = ""
    duration: int = 0
    tags: list[str] = field(default_factory = list)

    # 收藏夹\个人空间
    favorites_name: str = ""
    favorites_id: int = 0
    favorites_owner: str = ""
    favorites_owner_id: int = 0
    space_owner: str = ""
    space_owner_id: int = 0

    # 其他
    video_quality: str = ""
    audio_quality: str = ""
    video_codec: str = ""

@dataclass
class DownloadInfo(InfoBase):
    # 类型相关
    type: int = 0
    media_type: int = 0

    # 进度相关
    speed: int = 0
    progress: int = 0
    total_size: int = 0
    downloaded_size: int = 0
    status: int = 0

    # 属性相关
    video_quality_id: int = 0
    audio_quality_id: int = 0
    video_codec_id: int = 0

    queue: list[str] = field(default_factory = list)
    files: dict = field(default_factory = dict)

    # 合并相关
    merge_video_audio: bool = False
    keep_original_files: bool = False

    video_parts_count: int = 0

    # 显示信息
    info_label: str = ""
    status_label: str = ""

@dataclass
class TaskInfo:
    Basic: BasicInfo = field(default_factory = BasicInfo)
    File: FileInfo = field(default_factory = FileInfo)
    Episode: EpisodeInfo = field(default_factory = EpisodeInfo)
    Download: DownloadInfo = field(default_factory = DownloadInfo)

    def to_dict(self):
        return asdict(self)
    
    def from_dict(self, data: dict):
        basic_data = data.get("Basic", {})
        file_data = data.get("File", {})
        episode_data = data.get("Episode", {})
        download_data = data.get("Download", {})

        self.Basic.from_dict(basic_data)
        self.File.from_dict(file_data)
        self.Episode.from_dict(episode_data)
        self.Download.from_dict(download_data)
