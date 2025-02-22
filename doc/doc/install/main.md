# 安装主程序
## 方式一：编译版
此方式可脱离 Python 环境独立运行，并集成 FFmpeg，适用于 Windows 用户。

[GitHub Release](https://github.com/ScottSloan/Bili23-Downloader/releases/tag/v1.55.0)  
[蓝奏云](https://wwx.lanzout.com/iJNAV2m5jdna)  

下载完成后，将压缩包解压，以管理员身份运行 GUI.exe，即可开始使用。  
若出现应用程序错误等问题，请尝试修复 DirectX 和 C++ 运行库。  

## 方式二：手动安装
此方式同时适用于 Windows/Linux/macOS 平台用户。

Python 版本要求为 3.10 及以上。

### 克隆仓库
```bash
git clone https://github.com/ScottSloan/Bili23-Downloader.git
cd Bili23-Downloader
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python3 GUI.py
```

### 安装 wxPython
对于 Linux 用户，pip 源中可能没有提供 wxPython 的包，需要手动编译或[从此下载](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04/)。  

手动编译请执行以下代码：

```bash
sudo apt install libgtk-3-dev

pip install wxPython
```