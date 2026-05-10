## 2.00.5 (2026-05-10)
### 修复
- 修复在移动硬盘 (如 exFAT, FAT32) 上下载时，因底层不支持稀疏文件 (Sparse File) 预分配而导致严重的 I/O 阻塞问题。

### 注意
安装前请先移除旧版本，请勿覆盖安装。  
另外，新版本调整了 Linux/ macOS 发行版的系统需求，请确保系统满足以下要求：
#### Linux
- **AMD64架构**: Ubuntu 20.04 / Debian 11 / Fedora 32 / RHEL 9 及以上版本 (glibc 2.31+)
- **ARM64架构**: Ubuntu 24.04 / Debian 13 / Fedora 40 / RHEL 10 及以上版本 (glibc 2.39+)
#### macOS
- **x86_64架构**: macOS 12+
- **aarch64(Apple Silicon) 架构**: macOS 12+