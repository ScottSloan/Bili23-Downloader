import os

class Config:
    download_path = os.path.join(os.getcwd(), "download")
    cookie_sessdata = "33d5b4d7%2C1656815503%2Cf8311%2A11"

    show_sections = False

    save_danmaku = False

    save_subtitles = True

    _version = "1.12_pre-release"
    _date = "2022-2-20"
    _logo = os.path.join(os.getcwd(), "Pic", "logo.png")

    _info_base_path = os.path.join(os.getcwd(), "preview_info")
    _info_video_path = os.path.join(_info_base_path, "video_info.html")
    _info_bangumi_path = os.path.join(_info_base_path, "bangumi_info.html")
    _info_html = os.path.join(_info_base_path, "info.html")
    _info_cover = "cover"
