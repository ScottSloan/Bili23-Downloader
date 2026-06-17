from PySide6.QtCore import QCoreApplication

from functools import wraps

# alias
translate = QCoreApplication.translate

def get_map_method(func):
    @wraps(func)
    def wrapper(key = None, *args, **kwargs):
        mapping: dict = func(key, *args, **kwargs)

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
            "INTERACTIVE_VIDEO": translate("EPISODE_TYPE", "Interactive Video"),
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
            "PROFILE": translate("EPISODE_TYPE", "Profile"),
            "WATCH_LATER": translate("EPISODE_TYPE", "Watch Later"),
            "HISTORY": translate("EPISODE_TYPE", "History"),
            "AUDIO": translate("EPISODE_TYPE", "Music")
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
            "DEFAULT_FOR_PART": translate("DEFAULT_RULE_NAMES", "Preset: Multi-part Series"),
            "DEFAULT_FOR_COLLECTION": translate("DEFAULT_RULE_NAMES", "Preset: Collection"),
            "DEFAULT_FOR_INTERACTIVE_VIDEO": translate("DEFAULT_RULE_NAMES", "Preset: Interactive Video"),
            "DEFAULT_FOR_BANGUMI": translate("DEFAULT_RULE_NAMES", "Preset: Film & TV"),
            "DEFAULT_FOR_CHEESE": translate("DEFAULT_RULE_NAMES", "Preset: Courses"),
            "DEFAULT_FOR_FAVORITE": translate("DEFAULT_RULE_NAMES", "Preset: Favorites"),
            "DEFAULT_FOR_SPACE": translate("DEFAULT_RULE_NAMES", "Preset: Profile"),
            "DEFAULT_FOR_AUDIO": translate("DEFAULT_RULE_NAMES", "Preset: Music"),
            "DEFAULT_FOR_HISTORY": translate("DEFAULT_RULE_NAMES", "Preset: History"),
            "DEFAULT_FOR_WATCH_LATER": translate("DEFAULT_RULE_NAMES", "Preset: Watch Later")
        }

    @staticmethod
    @get_map_method
    def CONVENTION_TYPE(key = None):
        return {
            "NORMAL": translate("CONVENTION_TYPE", "Single Video"),
            "PART": translate("CONVENTION_TYPE", "Multi-part Series"),
            "COLLECTION": translate("CONVENTION_TYPE", "Collection"),
            "INTERACTIVE_VIDEO": translate("CONVENTION_TYPE", "Interactive Video"),
            "BANGUMI": translate("CONVENTION_TYPE", "Film & TV"),
            "CHEESE": translate("CONVENTION_TYPE", "Courses"),
            "FAVORITE": translate("CONVENTION_TYPE", "Favorites"),
            "SPACE": translate("CONVENTION_TYPE", "Profile"),
            "HISTORY": translate("CONVENTION_TYPE", "History"),
            "WATCH_LATER": translate("CONVENTION_TYPE", "Watch Later"),
            "AUDIO": translate("CONVENTION_TYPE", "Music")
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
            "UPLOADER_FOR_AUDIO": translate("VARIABLE_DESCRIPTION", "Author of the song"),
            "UPLOADER_UID": translate("VARIABLE_DESCRIPTION", "Uploader id"),
            "VIDEO_QUALITY": translate("VARIABLE_DESCRIPTION", "Video quality"),
            "AUDIO_QUALITY": translate("VARIABLE_DESCRIPTION", "Audio quality"),
            "VIDEO_CODEC": translate("VARIABLE_DESCRIPTION", "Video codec"),

            "AID": translate("VARIABLE_DESCRIPTION", "av number"),
            "BVID": translate("VARIABLE_DESCRIPTION", "BV number"),
            "CID": translate("VARIABLE_DESCRIPTION", "cid"),
            "EP_ID": translate("VARIABLE_DESCRIPTION", "Episode id"),
            "SEASON_ID": translate("VARIABLE_DESCRIPTION", "Season id"),

            "LEAF_TITLE_FOR_NORMAL": translate("VARIABLE_DESCRIPTION", "Full video title"),
            "LEAF_TITLE_FOR_PART": translate("VARIABLE_DESCRIPTION", "Current part's title"),
            "LEAF_TITLE_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Content title (video title for single videos, part title for multi-part)"),
            "LEAF_TITLE_FOR_INTERACTIVE_VIDEO": translate("VARIABLE_DESCRIPTION", "Node title"),
            "LEAF_TITLE_FOR_AUDIO": translate("VARIABLE_DESCRIPTION", "Song title"),

            "PARENT_TITLE_FOR_PART": translate("VARIABLE_DESCRIPTION", "Multi-part video main title"),
            "PARENT_TITLE_FOR_COLLECTION": translate("VARIABLE_DESCRIPTION", "Main title if video has multiple parts; otherwise empty"),
            "PARENT_TITLE_FOR_INTERACTIVE_VIDEO": translate("VARIABLE_DESCRIPTION", "Interactive video title"),
            "PARENT_TITLE_FOR_HISTORY": translate("VARIABLE_DESCRIPTION", "History title"),
            "PARENT_TITLE_FOR_WATCH_LATER": translate("VARIABLE_DESCRIPTION", "Watch Later title"),
            "PARENT_TITLE_FOR_AUDIO": translate("VARIABLE_DESCRIPTION", "Playlist title"),

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

            "FAVORITES_NAME": translate("VARIABLE_DESCRIPTION", "Favorites name"),
            "FAVORITES_ID": translate("VARIABLE_DESCRIPTION", "Favorites id"),
            "FAVORITES_OWNER": translate("VARIABLE_DESCRIPTION", "Favorites owner"),
            "FAVORITES_OWNER_ID": translate("VARIABLE_DESCRIPTION", "Favorites owner id"),

            "SPACE_OWNER": translate("VARIABLE_DESCRIPTION", "User name"),
            "SPACE_OWNER_ID": translate("VARIABLE_DESCRIPTION", "User id")
        }

    @staticmethod
    def COLUMN_NAME(key: str, category_name: str = None):
        map = {
            "number": translate("COLUMN_NAME", "No."),
            "title": translate("COLUMN_NAME", "Title"),
            "badge": translate("COLUMN_NAME", "Notes"),
            "duration": translate("COLUMN_NAME", "Duration"),
            "dyn_time": translate("COLUMN_NAME", "Publish / Favorite / Watch Time"),
            "pubtime": translate("COLUMN_NAME", "Publish Time"),
            "favtime": translate("COLUMN_NAME", "Favorite Time"),
            "viewtime": translate("COLUMN_NAME", "Watch Time"),
        }
        
        if key == "pub_fav_time" and category_name is not None:
            if category_name == "FAVORITES":
                return map["favtime"]
            else:
                return map["pubtime"]
        else:
            return map.get(key, key)

    @staticmethod
    @get_map_method
    def ERROR_MESSAGES(key = None):
        return {
            "FFMPEG_FAILED": translate("ERROR_MESSAGES", "An error occurred while running FFmpeg"),
            "FFMPEG_FAILED_WITH_CODE": translate("ERROR_MESSAGES", "FFmpeg failed with exit code {code}"),
            "FILE_NOT_FOUND": translate("ERROR_MESSAGES", "The specified file or folder does not exist, you may need to download it again."),
            "FILE_NOT_FOUND_DETAIL": translate("ERROR_MESSAGES", "The file may have been moved or deleted. Please download it again."),
            "INSUFFICIENT_SPACE": translate("ERROR_MESSAGES", "Insufficient disk space, please free up enough space and try again."),
            "PERMISSION_DENIED": translate("ERROR_MESSAGES", "Permission denied: cannot write to file"),
            "CORRUPTED_FILE": translate("ERROR_MESSAGES", "Downloaded file is corrupted, please try downloading again."),
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
            "FFMPEG_PROCESSING_FAILED": translate("ERROR_MESSAGES", "FFmpeg processing failed"),
            "M4A_NOT_FOUND": translate("ERROR_MESSAGES", "M4A audio file not found for conversion"),
            "LOGIN_REQUIRED": translate("ERROR_MESSAGES", "Login Required"),
            "LOGIN_REQUIRED_MESSAGE": translate("ERROR_MESSAGES", "Please log in to your account first."),
            "B23_TV_URL_EXPIRED": translate("ERROR_MESSAGES", "The b23.tv short link is invalid or has expired."),
            "INVALID_LINK": translate("ERROR_MESSAGES", "Invalid link format"),
            "PARSING_STOPPED": translate("ERROR_MESSAGES", "Parsing stopped"),
            "PARSING_STOPPED_MESSAGE": translate("ERROR_MESSAGES", "An error occurred during parsing, and the process has been stopped. Parsing was completed up to page {page}.\n\nReminder: Due to Bilibili's anti-abuse mechanism, parsing too many pages or at too high a frequency may result in failure and IP ban. Please use with caution!\n\n{error}")
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
            "EXPIRED": translate("TIP_MESSAGES", "Expired"),
            "ADDITIONAL_FILES": translate("TIP_MESSAGES", "Additional Files"),
            "DOWNLOADING_DANMAKU": translate("TIP_MESSAGES", "Downloading Danmaku..."),
            "DOWNLOADING_SUBTITLES": translate("TIP_MESSAGES", "Downloading Subtitles..."),
            "DOWNLOADING_COVER": translate("TIP_MESSAGES", "Downloading Cover..."),
            "SCRAPING_METADATA": translate("TIP_MESSAGES", "Scraping Metadata..."),
            "PARSING_INTERACTIVE_VIDEO_NODE": translate("TIP_MESSAGES", "Parsing node: {title}"),
            "PARSING_PAGE": translate("TIP_MESSAGES", "Parsing page {page}, total {total_page} pages, progress: {progress}%"),
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
        return translate("MEDIA_INFO_GUIDE", """The media info shown here defaults to the first video in the parsed results. If multiple videos are available, this information may not exactly match the one you download—use it for reference only.

To view detailed media info for a specific video, right-click its entry in the parse list and select "Update Media Info".
To customize the priority settings, go to the Settings page.

Note: Videos protected by DRM can only be downloaded up to 1080P; higher qualities are unavailable.""")
    
    @staticmethod
    def MEDIA_OPTIONS_GUIDE():
        return translate("MEDIA_OPTIONS_GUIDE", """Media options control how video and audio streams are downloaded and whether they are automatically merged after download.
Videos on Bilibili typically store and transmit video and audio streams separately. During download, both parts must be fetched individually and can then be merged into a complete video file using FFmpeg. These settings determine which streams to download and whether to keep the original unmerged files.

1. Download video and audio streams: If only the video stream is downloaded, the final file will have no audio; if only the audio stream is downloaded, you'll get an audio-only file. Only when both video and audio streams are downloaded can they be merged later into a complete video file with sound.

2. Merge video and audio: When enabled, the program will use FFmpeg to merge the two parts into a single complete video file after download. When disabled, the video and audio streams will be saved as separate files.

3. Keep original files: When enabled, the original video and audio stream files will be retained after merging. When disabled, the program will delete the original separated streams and keep only the merged complete video file.""")

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

    @staticmethod
    def PRIORITY_GUIDE():
        return translate("PRIORITY_GUIDE", """The program will attempt downloads in the order of your configured priority. The actual video quality, audio quality, or codec you can download still depends on what is available in the video itself—priority only determines which option is tried first among multiple available choices.

For example, if you set the video quality priority to 720P > 1080P > 4K, the program will first try to download 720P; if 720P is unavailable, it will then try 1080P and then 4K in sequence.""")
    
    @staticmethod
    def NUMBERING_GUIDE():
        return translate("NUMBERING_GUIDE", """This setting affects the value of the {number} variable in the naming rule. By default, the program’s preset naming rule does not include {number}. If you want to use numbering, please add {number} to your naming rule first.

The meaning of each "Numbering Mode" option is as follows:
1. Sequential numbering starting from 1 per batch: Every time a new download task begins, numbering restarts from 1. Suitable for scenarios where each batch should have independent numbering.

2. Use the index from the parsed list: The numbering directly reflects the original position in the parsed list and won’t change based on download order. For example, items at positions 3, 5, and 6 in the list will be numbered 3, 5, and 6 respectively. Suitable when you want numbering to match the parsing result exactly.

3. Global sequential numbering: All downloaded items share a single continuously incrementing sequence, regardless of series or batch. For example, if the last downloaded item was numbered 5, the next one will be 6. Suitable for maintaining a globally continuous numbering sequence.""")

    @staticmethod
    def PREALLOCATE_GUIDE():
        return translate("PREALLOCATE_GUIDE", """Preallocating file space can improve download performance, especially for large files. When enabled, the program will allocate the required disk space before the download starts, reducing performance overhead caused by repeatedly expanding the file during download and minimizing disk fragmentation.

Note: If the download path is on an external storage device such as a USB drive, and the file system does not support sparse files (e.g., FAT32 or exFAT), please disable this feature—otherwise, the program may become unresponsive.""")
    
    @staticmethod
    @get_map_method
    def ERROR_CODE_EXPLANATION(key = None):
        return {
            412: translate("ERROR_CODE_EXPLANATION", "Request blocked, client IP has been banned"),
            87008: translate("ERROR_CODE_EXPLANATION", "Paid content requires purchasing")
        }