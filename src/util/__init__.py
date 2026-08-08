# 此处不要导入子模块：util 是所有工具模块的父包，任何一次 from util.x import y 都会先执行
# 本文件，在这里做的初始化工作都会落到启动的关键路径上。FFmpeg 的探测改由 init_ffmpeg() 显式触发。
