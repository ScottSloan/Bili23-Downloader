from PySide6.QtCore import QCoreApplication

from functools import wraps

# alias
translate = QCoreApplication.translate

def get_map_method(func):
    @wraps(func)
    def wrapper(key = None):
        mapping: dict = func(key)

        if key is None:
            return mapping
        else:
            return mapping.get(key)
    
    return wrapper

class Translator:
    @staticmethod
    @get_map_method
    def CDN_SERVER_PROVIDER(key = None):
        return {
            "ALIYUN": translate("CDN_SERVER_PROVIDER", "Aliyun"),
            "TENCENT": translate("CDN_SERVER_PROVIDER", "Tencent Cloud"),
            "HUAWEI": translate("CDN_SERVER_PROVIDER", "Huawei Cloud"),
            "CUSTOM": translate("CDN_SERVER_PROVIDER", "Custom")
        }

    @staticmethod
    @get_map_method
    def VIDEO_QUALITY(key = None):
        return {
            "auto": translate("VIDEO_QUALITY", "Auto (by priority)"),
            "8K": translate("VIDEO_QUALITY", "8K UHD"),
            "DOLBY_VISION": translate("VIDEO_QUALITY", "Dolby Vision"),
            "HDR": translate("VIDEO_QUALITY", "HDR True Color"),
            "4K": translate("VIDEO_QUALITY", "4K UHD"),
            "1080P60": translate("VIDEO_QUALITY", "1080P 60fps"),
            "1080P+": translate("VIDEO_QUALITY", "1080P High Bitrate"),
            "AI": translate("VIDEO_QUALITY", "AI Upscale"),
            "1080P": translate("VIDEO_QUALITY", "1080P"),
            "720P": translate("VIDEO_QUALITY", "720P"),
            "480P": translate("VIDEO_QUALITY", "480P"),
            "360P": translate("VIDEO_QUALITY", "360P")
        }

    @staticmethod
    @get_map_method
    def AUDIO_QUALITY(key = None):
        return {
            "auto": translate("AUDIO_QUALITY", "Auto (by priority)"),
            "HI_RES": translate("AUDIO_QUALITY", "Hi-Res Audio"),
            "DOLBY_ATMOS": translate("AUDIO_QUALITY", "Dolby Atmos"),
            "192K": translate("AUDIO_QUALITY", "192 kbps"),
            "132K": translate("AUDIO_QUALITY", "132 kbps"),
            "64K": translate("AUDIO_QUALITY", "64 kbps")
        }
    
    @staticmethod
    @get_map_method
    def VIDEO_CODEC(key = None):
        return {
            "auto": translate("VIDEO_CODEC", "Auto (by priority)"),
            "AVC/H.264": translate("VIDEO_CODEC", "AVC/H.264"),
            "HEVC/H.265": translate("VIDEO_CODEC", "HEVC/H.265"),
            "AV1": translate("VIDEO_CODEC", "AV1")
        }

    @staticmethod
    @get_map_method
    def EPISODE_TYPE(key = None):
        return {
            "USER_UPLOADS": translate("EPISODE_TYPE", "User Uploads"),
            "INTERACTIVE": translate("EPISODE_TYPE", "Interactive Video"),
            "ANIME": translate("EPISODE_TYPE", "Anime"),
            "MOVIE": translate("EPISODE_TYPE", "Movies"),
            "DOCUMENTARY": translate("EPISODE_TYPE", "Documentaries"),
            "CHN_ANIME": translate("EPISODE_TYPE", "Chinese Animation"),
            "TV": translate("EPISODE_TYPE", "TV Dramas"),
            "VARIETY": translate("EPISODE_TYPE", "Variety Shows"),
            "COURSE": translate("EPISODE_TYPE", "Courses"),
            "WEEKLY": translate("EPISODE_TYPE", "Weekly Picks"),
            "PLAYLIST": translate("EPISODE_TYPE", "Playlists"),
            "FAVORITES": translate("EPISODE_TYPE", "Favorites"),
            "PROFILE": translate("EPISODE_TYPE", "Profile")
        }
    
    @staticmethod
    @get_map_method
    def DANMAKU_SPEED(key = None):
        return {
            "VERY_SLOW": translate("DANMAKU_SPEED", "Very Slow"),
            "SLOW": translate("DANMAKU_SPEED", "Slow"),
            "NORMAL": translate("DANMAKU_SPEED", "Normal"),
            "FAST": translate("DANMAKU_SPEED", "Fast"),
            "VERY_FAST": translate("DANMAKU_SPEED", "Very Fast"),
        }

    @staticmethod
    @get_map_method
    def DANMAKU_DENSITY(key = None):
        return {
            "NORMAL": translate("DANMAKU_DENSITY", "Normal"),
            "HIGH": translate("DANMAKU_DENSITY", "High"),
            "OVERLAP": translate("DANMAKU_DENSITY", "Overlap")
        }

    @staticmethod
    @get_map_method
    def SUBTITLES_ALIGNMENT(key = None):
        return {
            "BOTTOM_LEFT": translate("SUBTITLES_ALIGNMENT", "Bottom Left"),
            "BOTTOM_CENTER": translate("SUBTITLES_ALIGNMENT", "Bottom Center"),
            "BOTTOM_RIGHT": translate("SUBTITLES_ALIGNMENT", "Bottom Right"),
            "MIDDLE_LEFT": translate("SUBTITLES_ALIGNMENT", "Middle Left"),
            "MIDDLE_CENTER": translate("SUBTITLES_ALIGNMENT", "Middle Center"),
            "MIDDLE_RIGHT": translate("SUBTITLES_ALIGNMENT", "Middle Right"),
            "TOP_LEFT": translate("SUBTITLES_ALIGNMENT", "Top Left"),
            "TOP_CENTER": translate("SUBTITLES_ALIGNMENT", "Top Center"),
            "TOP_RIGHT": translate("SUBTITLES_ALIGNMENT", "Top Right"),
        }

    @staticmethod
    @get_map_method
    def DEFAULT_RULE_NAMES(key = None):
        return {
            "DEFAULT_FOR_NORMAL": translate("DEFAULT_RULE_NAMES", "Preset: Single Video"),
            "DEFAULT_FOR_PART": translate("DEFAULT_RULE_NAMES", "Preset: Multi-part Video"),
            "DEFAULT_FOR_COLLECTION": translate("DEFAULT_RULE_NAMES", "Preset: Collection"),
            "DEFAULT_FOR_BANGUMI": translate("DEFAULT_RULE_NAMES", "Preset: Series & Shows"),
            "DEFAULT_FOR_CHEESE": translate("DEFAULT_RULE_NAMES", "Preset: Courses")
        }

    @staticmethod
    @get_map_method
    def CONVENTION_TYPE(key = None):
        return {
            "NORMAL": translate("CONVENTION_TYPE", "User Uploads - Single"),
            "PART": translate("CONVENTION_TYPE", "User Uploads - Multi-part"),
            "COLLECTION": translate("CONVENTION_TYPE", "User Uploads - Collection"),
            "INTERACTIVE": translate("CONVENTION_TYPE", "User Uploads - Interactive"),
            "BANGUMI": translate("CONVENTION_TYPE", "Series & Shows"),
            "CHEESE": translate("CONVENTION_TYPE", "Courses"),
        }

    @staticmethod
    @get_map_method
    def VARIABLE_DESCRIPTION(key = None):
        return {
            "PUB_TIME": translate("VARIABLE_DESCRIPTION", "Video publish time"),
            "PUB_TS": translate("VARIABLE_DESCRIPTION", "Video publish timestamp"),
            "NUMBER": translate("VARIABLE_DESCRIPTION", "Sequence number"),
            "UPLOADER": translate("VARIABLE_DESCRIPTION", "Uploader name"),
            "UPLOADER_UID": translate("VARIABLE_DESCRIPTION", "Uploader UID"),

            "AID": translate("VARIABLE_DESCRIPTION", "av number"),
            "BVID": translate("VARIABLE_DESCRIPTION", "BV number"),
            "CID": translate("VARIABLE_DESCRIPTION", "cid"),
            "EP_ID": translate("VARIABLE_DESCRIPTION", "Episode id"),
            "SEASON_ID": translate("VARIABLE_DESCRIPTION", "Season id"),

            "LEAF_TITLE_FOR_NORMAL": translate("VARIABLE_DESCRIPTION", "Full video title"),
            "LEAF_TITLE_FOR_PART": translate("VARIABLE_DESCRIPTION", "Current part's title"),
            "LEAF_TITLE_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Content title (video title for single videos, part title for multi-part)"),

            "PARENT_TITLE_FOR_PART": translate("VARIABLE_DESCRIPTION", "Multi-part video main title"),
            "PARENT_TITLE_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Main title if video has multiple parts; otherwise empty"),

            "PART_NUMBER_FOR_PART": translate("VARIABLE_DESCRIPTION", "Part number"),
            "PART_NUMBER_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Part number (only for multi-part videos)"),

            "COLLECTION_TITLE": translate("VARIABLE_DESCRIPTION", "Collection title"),
            "SECTION_TITLE_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Section title (empty if not divided into sections)"),
            "SECTION_TITLE_FOR_BANGUMI_CHEESE": translate("VARIABLE_DESCRIPTION", "Section title"),

            "SERIES_TITLE_FOR_BANGUMI": translate("VARIABLE_DESCRIPTION", "Series title"),
            "SERIES_TITLE_FOR_CHEESE": translate("VARIABLE_DESCRIPTION", "Courses title"),
            "SEASON_TITLE": translate("VARIABLE_DESCRIPTION", "Season title"),
            "EPISODE_TITLE": translate("VARIABLE_DESCRIPTION", "Episode title"),
            "SEASON_NUMBER": translate("VARIABLE_DESCRIPTION", "Season number"),
            "EPISODE_NUMBER": translate("VARIABLE_DESCRIPTION", "Episode number"),
        }

    @staticmethod
    def MEDIA_INFO_GUIDE():
        return translate("MEDIA_INFO_GUIDE", """The media info shown here defaults to the first video in the parsed results. If multiple videos are available,
this information may not exactly match the one you download—use it for reference only.

To view detailed media info for a specific video, right-click its entry in the parse list and select "View Media Info".
To customize the priority settings, go to the Settings page.

Note: Videos protected by DRM can only be downloaded up to 1080P; higher qualities are unavailable.""")

    @staticmethod
    def NAMING_RULE_GUIDE():
        return translate("NAMING_RULE_GUIDE", """Customize the file name and folder structure using variables.

Rules:
1. Use {variable} to insert dynamic values (e.g., {uploader}, {leaf_title}).
2. Use "/" to create folders — don't start or end with "/".
3. The part after the last "/" is the file name; before it is the directory.
4. Available variables depend on the naming rule type (see list below).
5. File extensions (.mp4, .m4a, etc.) are added automatically — don’t include them.

Examples:
• {uploader}/{leaf_title} → Saves as "Video Title" inside "Uploader" folder
• {uploader}_{leaf_title} → Saves directly as "Uploader_Video Title"
                         
For advanced usage, see the help documentation.""")