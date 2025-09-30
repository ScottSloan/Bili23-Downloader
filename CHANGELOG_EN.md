## 1.70.0 (2025-09-30) EN
### Added
* Support for setting ASS danmaku display area, opacity, danmaku speed, danmaku density, and anti-overlap subtitles
* Support for scaling, rotating, and adjusting character spacing for ASS danmaku/subtitles
* Support for downloading NFO and JSON format metadata
* Support for setting priority of video quality, audio quality, and encoding format
* Support for batch selection of episode list items by holding the Shift key
* When parsing favorites and user homepages, support for manually selecting the number of pages to parse
* When downloading episodes, support for strictly standardized naming for better compatibility with scraping software
* Support for converting downloaded m4a audio files to mp3 format
* Added English language support

### Improved
* Optimized the movement speed algorithm for ASS scrolling danmaku
* Improved some UI display effects
* Optimized the logic for parsing favorites and user homepages to avoid risk control interception
* Improved parsing speed
* Improved stability when downloading large files
* Adjusted some video quality option names, e.g., 1080P+ -> 1080P High Bitrate, 1080P60 -> 1080P 60fps

### Fixed
* Fixed the issue where batch downloading of danmaku/subtitles/covers individually was not constrained by the parallel download setting
* Fixed the issue of abnormal ASS subtitle color display on Linux
* Fixed the issue where the installer could not access configuration files in the Program Files folder
* Fixed the issue where editing the filename template did not take effect
* Fixed the issue where error messages were displayed abnormally when parsing episodes