# PyStand

> **本目录是 Bili23 Downloader 的 Windows 启动器**，fork 自
> [skywind3000/PyStand](https://github.com/skywind3000/PyStand)（MIT，原文见
> 本目录 `LICENSE`），并做了下述定制。**下面「特性介绍」以后的部分是上游的
> 通用说明，讲的是未定制版的 PyStand 用法**（磁盘入口脚本、`PyStand.int`、
> 手工铺 site-packages 等），本项目已不再走那条路径 —— 阅读时请以这一段为准。
>
> ## 相对上游的定制
>
> - **应用源码内嵌**（`PYSTAND_EMBED_APP`）：`src/` 打成 app.zip 存进 exe 的
>   资源段，每个模块存 `.py`（供 traceback 的 `get_source()`）与 `.pyc`
>   （供执行）两份。`DetectScript()` 在内嵌模式下**直接返回**，不再探测磁盘上的
>   `.int` / `.py` —— 只要还认外部入口，往目录里放个同名文件就能绕开内嵌源码，
>   签过名的启动器又变回了谁都能拿去跑任意代码的通用 loader。
> - **完整性清单**（`INTEGRITY` 资源）：列出每个随包文件的 SHA-256，加载 Python
>   之前逐个核对；受管目录（`runtime` / `site-packages` / `bundle` / `webui`）
>   下出现清单外的可执行类型一律拒绝启动，挡的是 `.pth` 注入与 DLL 投放。
>   清单与源码一样嵌在资源段里，跟着 exe 一起被 Authenticode 覆盖 ——
>   因此不需要私钥或非对称签名：改清单就得改 exe，签名当场失效。
> - **加固**：`SetDefaultDllDirectories` 收紧 DLL 搜索路径（Win7 上动态取地址，
>   取不到则退回 `SetDllDirectory`）；`-X utf8` 强制 UTF-8 模式；stdout/stderr
>   的接管改成**兜底**而非无条件 —— 进程被父进程用管道拉起时（MCP 的 stdio
>   桥接），无条件 `freopen` 会把唯一的输出通道换成 devnull。
> - **版本号单一来源**：从 `src/util/common/config.py` 的 `app_version` 读出，
>   由 CMake 注入 `resource.rc` 与 `main.manifest.in`，不在这里手工维护。
>
> ## 构建
>
> 不单独编译这个目录，走仓库根下的打包脚本 —— 它按「铺 runtime → 打包源码 →
> 生成清单 → 编译并嵌入 → 放入 exe」的顺序走完，顺序不可换（清单必须在 exe
> 就位前生成，它覆盖的正是随包的其他文件，且不含 exe 自己）：
>
> ```powershell
> .\scripts\build_release.ps1 -RuntimeDir <Python 静态运行时目录> -OutputDir .\release
> ```
>
> 产出的是**未签名**的 exe，签名另做。

Python 独立部署环境。Python 3.5 以后，Windows 下面都有一个 Embedded Python 的独立 Python 运行环境，这个 PyStand 就是配合 Embedded Python 使用的。

## 特性介绍

- 使用 PyStand + PyQt5 精简版发布 PyQt 程序，打包大小只有 14MB。
- 使用 PyStand 发布普通 Python 程序，打包大小仅 5MB。

## 功能说明

- Windows 下独立 Python 环境的启动器。
- 自动加载 `PyStand.exe` 同级目录下面 `runtime` 子目录内的 Embedded Python。
- 自动启动 `PyStand.exe` 同级目录下面的 `PyStand.int` 程序（Python 代码）。
- 如果改名，会加载对应名称的 `.int` 文件，比如改为 `MyDemo.exe` 就会加载 `MyDemo.int`。
- 窗口程序，无 Console，但是如果在 cmd.exe 内运行，可以看到 print 的内容。
- 会自动添加 `PyStand.exe` 同级目录下的 `site-packages` 目录，库可以放到里面。

## 使用方式

- 用 CMake 生成 `PyStand.exe` （或者到 Release 里下个现成的）。
- 下载 Python Embedded 版本，放到 `PyStand.exe` 所在目录的 runtime 子目录内。
- 注意 Python Embedded 如果是 32 位，PyStand 配置 CMake 时也需要指明 `-A Win32`。
- 在 `PyStand.exe` 所在目录创建 Python 源代码 PyStand.int。
- 双击 `PyStand.exe` 就会运行 `PyStand.int` 里的代码。
- 可以编译成命令行版方便调试，CMake 的时候加 `-DPYSTAND_CONSOLE=ON` 即可。

## 常见问题

### 安装依赖

用一个同 Embedded Python 相同版本的 Python 做一个 venv，然后 `pip` 独立安装好模块后将 site-packages 内对应的包复制到 `PyStand.exe` 的 `site-packages` 下直接使用。

### 查看错误

如果在 `cmd.exe` 内部运行 `PyStand.exe` 可以看到标准输出和标准错误。不过推荐的做法是 PyStand.int 里尽量精简，比如：

```python
import main
main.main()
```

把你的主程序写到 `main.py` 里面，用你常规方式把程序调试通顺了，然后再在 `PyStand.int` 里 `import` 一下即可，实在 `PyStand.int` 有错误，再到命令行下面去运行 `PyStand.exe` 查看错误。

### MessageBox

PyStand 添加了一个 `os.MessageBox(msg, title)` 的接口，可以用来简单显示个对话框。

### 更换图标

可以替换 `appicon.ico` 文件并重新编译 `PyStand.exe` ，或者使用 `Resource Hacker` 直接
替换 `Release` 内下载的 `PyStand.exe` 文件的程序图标。

### 脚本组织

可以在 `PyStand.exe` 同级目录新建一个 `script` 文件夹，将脚本放进去，`PyStand.int` 里面就是添加一下 `sys.path` 然后 `import` 即可。

发布打包时将 `script` 文件夹用 `zip` 压缩成 `script.egg` 文件，`PyStand.int` 里检测到该文件存在就加入到 `sys.path`，然后再 `import`。

### 静态入口

部分网友有个需求，担心用户把可执行文件改名，但 `.int` 文件没改名导致出错的问题，因此增加了一个名为 `_pystand_static.int` 的入口文件，在 `PyStand` 主程序启动时，如果检测到在主程序同目录下存在该文件，则会优先加载，不存在才回去找 `PyStand.int` 文件。

这样主程序就允许随意改名了，只要把入口写在 `_pystand_static.int` 中即可。

## 使用例子

这个回答里我说了详细的用法以及 PyInstaller 的优缺点：

- [Skywind Inside：打包 PyQt 应用的最佳方案是什么？](https://skywind.me/blog/archives/3002)

更多的用法可以见 Release 下面的例子。

## 常见问题

其他用户使用中碰到什么疑问？如何解决的？

- [Wiki：常见问题](https://github.com/skywind3000/PyStand/wiki/Frequently-Asked-Questions)

碰到疑问不妨快速过一下。




