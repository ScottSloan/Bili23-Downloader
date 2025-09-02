<script setup>
    import { version, zip_url, setup_url, setup_passwd, zip_sha1, setup_sha1 } from '../../project.json'
    
    let release_asset_zip = `Bili23_Downloader-${version}-windows-x64.zip`
    let release_asset_setup = `Bili23_Downloader-${version}-windows-x64-setup.exe`

    let release_asset_github = (version, file)=> {
        return `https://github.com/ScottSloan/Bili23-Downloader/releases/download/v${version}/${file}`
    }
</script>

# 安装程序
## 下载发行版
用户可前往 [GitHub Release](https://github.com/ScottSloan/Bili23-Downloader/releases/) 页面查看历史版本，也可以在下方列表中根据需要选择下载。

| 文件名 | 平台架构 | 下载地址 | 备注 |
| --- | --- | --- | --- |
| Bili23 Downloader | Windows、Linux、macOS | <a href="https://github.com/ScottSloan/Bili23-Downloader" target="_blank" rel="noreferer">GitHub</a>| 源代码 |
| <span>Bili23_Downloader-{{ version }}-</span><br><span>windows-x64.zip</span> | Windows x64 | <a :href="release_asset_github(version, release_asset_zip)" target="_blank" rel="noreferer">GitHub</a> <br> <a :href="zip_url" target="_blank" rel="noreferer">蓝奏云</a> | 解压即用 |
| <span>Bili23_Downloader-{{ version }}-</span><br><span>windows-x64-setup.exe</span> | Windows x64 | <a :href="release_asset_github(version, release_asset_setup)" target="_blank" rel="noreferer">GitHub</a> <br> <a :href="setup_url" target="_blank" rel="noreferer">蓝奏云</a> | 独立安装程序 <br> 密码：{{ setup_passwd }} |

::: warning 重要提示
若您使用的是编译版，请先确保安装 Microsoft Visual C++ 2015-2022 运行库，否则无法运行本程序。
如果未安装，请[点击此处](https://aka.ms/vs/17/release/vc_redist.x64.exe)下载安装。
:::

::: info 社区交流
欢迎[加入社区](https://bili23.scott-sloan.cn/doc/community.html)，获取项目最新动态、问题答疑和技术交流。
:::

文件 SHA1 值校验
| 文件名 | SHA1 |
| -- | -- |
| <span>Bili23_Downloader-{{ version }}-</span><br><span>windows-x64.zip</span> | {{ zip_sha1 }} |
| <span>Bili23_Downloader-{{ version }}-</span><br><span>windows-x64-setup.exe</span> | {{ setup_sha1 }} |

:::tip
下载完成后建议校验 SHA1 值，防止程序被篡改。  

本程序完全开源免费，若是从其他渠道付费获取的，无法保证其安全性和完整性。  

本程序发行版使用 Nuitka 编译，可能会被防病毒软件误报。如果对防病毒软件报毒有疑问的，请删除本程序，使用其他同类工具。  

VirScan 在线病毒检测报告请[点此查看](https://www.virscan.org/report/c38475156fc01dd2c4f5c0291151ef872e38d1749e3cc01e438393f9aa545c3c)。
:::

### 如何校验 SHA1
::: details 查看校验方法
#### Windows
```bash
certutil -hashfile <file> SHA1
```

#### Linux
```bash
sha1sum <file>
```

#### macOS
```bash
shasum -a 1 <file>
```
:::

## 源码版使用
### 安装 Python 环境
Python 版本需要为 3.10 及以上。

::: details 如果还未安装 Python 环境，点击查看安装方式
从[Python官网](https://www.python.org/)下载系统对应的 Python，建议使用 3.11 及以上版本，最低支持 3.10 版本。  

若下载速度缓慢，建议使用国内[华为云镜像源](https://mirrors.huaweicloud.com/python/)下载。  

安装时注意勾选`Add python.exe to PATH`，创建环境变量。  

[![pElIuQJ.png](https://s21.ax1x.com/2025/02/23/pElIuQJ.png)](https://imgse.com/i/pElIuQJ)

完成 Python 环境安装后，建议执行下面的命令更换 pip 源为清华源，加快 pip 包下载速度：
```bash
pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```
:::

### 克隆仓库
若已安装 git，执行以下命令克隆仓库：
```bash
git clone https://github.com/ScottSloan/Bili23-Downloader.git
cd Bili23-Downloader
```

若系统未安装 git，请下载上方的源码版并解压，进入到 requirements.txt 同一级目录。

### 安装依赖
#### Windows & macOS
Windows 和 macOS 用户可以执行下面的命令一键安装所需依赖：

```bash
pip install -r requirements.txt
```

下表为程序所需依赖：
| 包 | 版本 | 备注 |
| -- | -- | -- |
| requests | ==2.32.5 | - |
| wxPython | ==4.2.3 | - |
| qrcode[pil] | ==7.4.2 | 必须附带 [pil]（Pillow），否则程序可能无法运行 |
| python-vlc | ==3.0.21203 | - |
| protobuf | ==6.32.0 | - |
| websockets | ==15.0.1 | -- |
| pycryptodome | ==3.23.0 | -- |

用户也可以手动安装：
```bash
pip install wxPython==4.2.3 qrcode[pil]==7.4.2 requests==2.32.5 python-vlc==3.0.21203 protobuf==6.32.0 websockets==15.0.1 pycryptodome==3.23.0
```
#### Linux
由于 Linux 平台各发行版存在差异，wxPython 安装较为繁琐，以下提供最简便的安装方式。
wxPython 官方提供 Debian、Ubuntu、Fedora 和 Centos 等发行版 wheel 包，点击[此处](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/)跳转。

以 Ubuntu 24.04 系统为例，执行下面的命令即可安装：
```bash
pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-24.04/ wxPython
```

随后再安装其他依赖：
```bash
pip install qrcode[pil]==7.4.2 requests==2.32.5 python-vlc==3.0.21203 protobuf==6.32.0 websockets==15.0.1 pycryptodome==3.23.0
```

### 安装 FFmpeg
程序依赖 FFmpeg 实现音视频合成，格式转换，直播录制等功能，缺少时将影响正常使用。  

有关 FFmpeg 的安装，请参考[下一页](https://bili23.scott-sloan.cn/doc/install/ffmpeg.html)内容。  

:::tip
若使用的是附带 FFmpeg 的编译版，无需再次安装。
:::

### 运行程序
直接运行 GUI.py 即可打开程序：

```bash
cd src
python3 GUI.py
```

## 编译版使用
下载完成后，解压压缩包，`以管理员身份`运行 GUI.exe，即可开始使用。 

:::tip
若出现应用程序错误等问题，请尝试修复 DirectX 和 C++ 运行库。  
:::