@echo off
chcp 65001 >nul
title Bili23 Downloader - 启动工具

echo ========================================
echo    Bili23 Downloader - 启动工具
echo ========================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 显示 Python 版本
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [信息] %PYTHON_VERSION%
echo.

:: 检查依赖是否安装
echo [检查] 正在检查依赖...
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [警告] 缺少 PySide6 依赖
    echo.
    choice /C YN /M "是否现在安装依赖（需要联网）"
    if errorlevel 2 (
        echo.
        echo [提示] 请手动运行以下命令安装依赖:
        echo   pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [安装] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败，请检查网络连接或手动安装
        echo.
        pause
        exit /b 1
    )
    echo [完成] 依赖安装成功
    echo.
) else (
    echo [完成] PySide6 已安装
)

python -c "import yt_dlp" >nul 2>&1
if errorlevel 1 (
    echo [警告] 缺少 yt-dlp，正在安装...
    pip install yt-dlp
    echo.
) else (
    echo [完成] yt-dlp 已安装
)

echo.
echo ========================================
echo [启动] 正在启动 Bili23 Downloader...
echo ========================================
echo.

python src\main.py

:: 如果程序异常退出
if errorlevel 1 (
    echo.
    echo ========================================
    echo [错误] 程序异常退出
    echo ========================================
    echo.
    echo 请检查上方错误信息，或尝试以下操作:
    echo 1. 重新安装依赖: pip install -r requirements.txt
    echo 2. 查看日志文件获取详细错误信息
    echo.
    pause
)