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
            "COLLECTION_LIST": translate("EPISODE_TYPE", "Collection"),
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
            "CREATE_TIME": translate("VARIABLE_DESCRIPTION", "Download task creation time"),
            "CREATE_TS": translate("VARIABLE_DESCRIPTION", "Download task creation timestamp"),
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
    @get_map_method
    def ERROR_MESSAGES(key = None):
        return {
            "FFMPEG_FAILED": translate("ERROR_MESSAGES", "An error occurred while running FFmpeg"),
            "FFMPEG_FAILED_WITH_CODE": translate("ERROR_MESSAGES", "FFmpeg failed with exit code {code}"),
            "FILE_NOT_FOUND": translate("ERROR_MESSAGES", "The specified file or folder does not exist"),
            "INSUFFICIENT_SPACE": translate("ERROR_MESSAGES", "Insufficient disk space"),
            "PERMISSION_DENIED": translate("ERROR_MESSAGES", "Permission denied: cannot write to file"),
            "CORRUPTED_FILE": translate("ERROR_MESSAGES", "Downloaded file is corrupted"),
            "COULD_NOT_OPEN": translate("ERROR_MESSAGES", "Failed to open file"),
            "FILE_IS_BUSY": translate("ERROR_MESSAGES", "File is in use by another process"),
            "CANNOT_CREATE": translate("ERROR_MESSAGES", "Could not create output file"),
            "DOWNLOAD_FAILED": translate("ERROR_MESSAGES", "Download failed"),
            "RENAME_FAILED": translate("ERROR_MESSAGES", "Failed to rename file"),
            "PARSE_FAILED": translate("ERROR_MESSAGES", "Failed to parse download information"),
            "MEDIA_INFO_FAILED": translate("ERROR_MESSAGES", "Failed to retrieve media information"),
            "LOGIN_EXPIRED": translate("ERROR_MESSAGES", "Login status expired"),
            "LOGIN_EXPIRED_MESSAGE": translate("ERROR_MESSAGES", "Your account login status has expired. Please log in again."),
            "USER_INFO_FAILED": translate("ERROR_MESSAGES", "Failed to retrieve user information"),
            "USER_AVATAR_FAILED": translate("ERROR_MESSAGES", "Failed to retrieve user avatar"),
            "LOGOUT_FAILED": translate("ERROR_MESSAGES", "Logout failed"),
            "UNKNOWN_ERROR": translate("ERROR_MESSAGES", "An unknown error occurred"),
            "CHECK_UPDATE_FAILED": translate("ERROR_MESSAGES", "Failed to check for updates"),
            "FFMPEG_PROCESSING_FAILED": translate("ERROR_MESSAGES", "FFmpeg processing failed")
        }

    @staticmethod
    @get_map_method
    def TIP_MESSAGES(key = None):
        return {
            "QUEUED": translate("TIP_MESSAGES", "Queued..."),
            "PARSING": translate("TIP_MESSAGES", "Parsing..."),
            "PAUSED": translate("TIP_MESSAGES", "Paused"),
            "FFMPEG_QUEUED": translate("TIP_MESSAGES", "Queued for FFmpeg..."),
            "MERGING": translate("TIP_MESSAGES", "Merging..."),
            "COMPLETED": translate("TIP_MESSAGES", "Completed"),
            "CONVERTING": translate("TIP_MESSAGES", "Converting..."),
            "ALREADY_LATEST_VERSION": translate("TIP_MESSAGES", "You are already using the latest version"),
            "DOWNLOAD_COMPLETED": translate("TIP_MESSAGES", "Download completed"),
            "DOWNLOAD_COMPLETED_DETAIL": translate("TIP_MESSAGES", "All download tasks have been completed."),
        }

    @staticmethod
    @get_map_method
    def ADDITIONAL_FILES_QUALIFIER(key = None):
        return {
            "DANMAKU": translate("ADDITIONAL_FILES_QUALIFIER", "Danmaku"),
            "SUBTITLES": translate("ADDITIONAL_FILES_QUALIFIER", "Subtitles"),
            "METADATA": translate("ADDITIONAL_FILES_QUALIFIER", "Metadata")
        }

    @staticmethod
    def MEDIA_INFO_GUIDE():
        return translate("MEDIA_INFO_GUIDE", """The media info shown here defaults to the first video in the parsed results. If multiple videos are available,
this information may not exactly match the one you download—use it for reference only.

To view detailed media info for a specific video, right-click its entry in the parse list and select "Update Media Info".
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
    
    @staticmethod
    def TERMS_OF_USE():
        return translate("TERMS_OF_USE", """<html>This software is intended solely for personal learning and research purposes. Any content downloaded through this project <b>is strictly limited to personal, non-commercial use and must not be used for any commercial purpose, public distribution, sharing, resale, or unlawful profit.</b>
<br><br>
This software operates exclusively based on the user's own legitimate account access rights and <b>does not bypass any paywalls, membership restrictions, or technical protection measures.</b> You may only download content that you are authorized to access through your normal login on the target platform. If your account does not have permission to access certain content, this software must not be used to obtain it.
<br><br>
<b>Do not use this software for bulk scraping, unauthorized redistribution of content, or any activity that violates the terms of service of the target platform.</b> You assume full responsibility for any consequences arising from your use, including but not limited to account suspension, copyright disputes, or other legal issues.
<br><br>
Under no circumstances shall the developer be liable for any direct, indirect, incidental, or consequential damages resulting from the use of or inability to use this software. By using this software, you acknowledge that you fully understand the above risks and voluntarily accept all associated responsibilities.
<br><br>
<b>Continuing to use this software indicates that you have read, understood, and agreed to comply with all the terms stated above.</b></html>""")
