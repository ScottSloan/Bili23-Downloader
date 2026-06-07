#!/bin/bash
set -euo pipefail

# ============================================================
# bili23-AISum - macOS 打包脚本
# 支持 arm64 (Apple Silicon) 和 x86_64 (Intel) 双架构
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build_output"
CACHE_DIR="$BUILD_DIR/.cache"

APP_NAME="bili23-AISum"
BUNDLE_ID="com.scottsloan.bili23-aisum"
VERSION="2.00.7"
VERSION_NAME="2.00.7"
MIN_MACOS="12.0"

# 自动检测架构
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    RUNTIME_ARCH="aarch64"
elif [ "$ARCH" = "x86_64" ]; then
    RUNTIME_ARCH="x86_64"
else
    echo "ERROR: 不支持的架构: $ARCH"
    exit 1
fi

# 可通过命令行参数覆盖架构
TARGET_ARCH="${1:-$ARCH}"
if [ "$TARGET_ARCH" = "arm64" ]; then
    RUNTIME_ARCH="aarch64"
elif [ "$TARGET_ARCH" = "x86_64" ]; then
    RUNTIME_ARCH="x86_64"
else
    echo "用法: $0 [arm64|x86_64]"
    echo "默认架构: $ARCH"
    exit 1
fi

echo "========================================"
echo "  bili23-AISum macOS 打包工具"
echo "  版本: $VERSION_NAME"
echo "  目标架构: $TARGET_ARCH"
echo "========================================"

# ---------- URL 配置 ----------
PYTHON_STATIC_VERSION="v0.0.9"
FFMPEG_MACOS_VERSION="8.0"

PYTHON_RUNTIME_URL="https://github.com/ScottSloan/Python-Static/releases/download/${PYTHON_STATIC_VERSION}/macos_${RUNTIME_ARCH}_runtime.zip"
FFMPEG_URL_ARM64="https://github.com/ScottSloan/Bili23-Down-and-Sum/releases/download/deps/ffmpeg-${FFMPEG_MACOS_VERSION}-arm64-macos.zip"
FFMPEG_URL_X86_64="https://github.com/ScottSloan/Bili23-Down-and-Sum/releases/download/deps/ffmpeg-${FFMPEG_MACOS_VERSION}-x86_64-macos.zip"

# ---------- 依赖检查 ----------
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: 缺少依赖 '$1'，请先安装: $2"
        exit 1
    fi
}

echo "[1/8] 检查构建依赖..."
check_dependency "python3" "brew install python3"
check_dependency "cmake" "brew install cmake"
check_dependency "wget" "brew install wget"
check_dependency "unzip" "brew install unzip"
check_dependency "zip" "系统已内置"

# 检查 create-dmg（可选，用于最终 DMG 生成）
HAS_CREATE_DMG=false
if command -v create-dmg &> /dev/null; then
    HAS_CREATE_DMG=true
else
    if command -v brew &> /dev/null; then
        echo "  create-dmg 未安装，将使用 hdiutil 替代（效果相同但无自定义图标布局）"
        echo "  建议安装: brew install create-dmg"
    else
        echo "  注: 将使用 hdiutil 生成 DMG"
    fi
fi

# ---------- 创建目录结构 ----------
echo ""
echo "[2/8] 创建构建目录..."
rm -rf "$BUILD_DIR/${APP_NAME}.app"
rm -rf "$BUILD_DIR/app_build"
mkdir -p "$CACHE_DIR"
mkdir -p "$BUILD_DIR/app_build/Contents/MacOS"
mkdir -p "$BUILD_DIR/app_build/Contents/Resources/runtime"
mkdir -p "$BUILD_DIR/app_build/Contents/Resources/bundle"
mkdir -p "$BUILD_DIR/app_build/Contents/Resources/script"

APP_RESOURCES="$BUILD_DIR/app_build/Contents/Resources"
APP_MACOS="$BUILD_DIR/app_build/Contents/MacOS"

# ---------- 下载 Python 静态运行时 ----------
echo ""
echo "[3/8] 下载 Python 静态运行时..."
RUNTIME_ZIP="$CACHE_DIR/macos_${RUNTIME_ARCH}_runtime.zip"

if [ ! -f "$RUNTIME_ZIP" ]; then
    echo "  下载: $PYTHON_RUNTIME_URL"
    wget -q --show-progress -O "$RUNTIME_ZIP" "$PYTHON_RUNTIME_URL" || {
        echo "ERROR: 下载 Python 运行时失败"
        echo "请检查网络连接或手动下载到: $RUNTIME_ZIP"
        exit 1
    }
else
    echo "  使用缓存: $RUNTIME_ZIP"
fi

echo "  解压..."
TEMP_RUNTIME="$BUILD_DIR/.runtime_extract"
rm -rf "$TEMP_RUNTIME"
mkdir -p "$TEMP_RUNTIME"
unzip -qo "$RUNTIME_ZIP" -d "$TEMP_RUNTIME"

# 复制运行时文件到 app bundle
cp -r "$TEMP_RUNTIME"/*/runtime/* "$APP_RESOURCES/runtime/" 2>/dev/null || cp -r "$TEMP_RUNTIME"/runtime/* "$APP_RESOURCES/runtime/" 2>/dev/null || {
    echo "  尝试直接复制运行时文件..."
    find "$TEMP_RUNTIME" -name "python3.*" -type f -exec cp {} "$APP_RESOURCES/runtime/" \; 2>/dev/null || true
}

# 复制 _pystand_static.int 入口脚本
PYSTAND_INT=$(find "$TEMP_RUNTIME" -name "_pystand_static.int" -type f 2>/dev/null | head -1)
if [ -f "$TEMP_RUNTIME/_pystand_static.int" ]; then
    cp "$TEMP_RUNTIME/_pystand_static.int" "$APP_RESOURCES/"
elif [ -n "$PYSTAND_INT" ]; then
    cp "$PYSTAND_INT" "$APP_RESOURCES/"
else
    echo "  WARNING: 未找到 _pystand_static.int 入口脚本"
fi

# 复制 bili23-downloader loader (如果存在)
LOADER_PATH="$APP_RESOURCES/bili23-downloader"
FOUND_LOADER=$(find "$TEMP_RUNTIME" -name "bili23-downloader" -type f 2>/dev/null | head -1)

if [ -f "$TEMP_RUNTIME/bili23-downloader" ]; then
    cp "$TEMP_RUNTIME/bili23-downloader" "$LOADER_PATH"
elif [ -n "$FOUND_LOADER" ]; then
    cp "$FOUND_LOADER" "$LOADER_PATH"
else
    echo "  注: 运行时 zip 中未找到 bili23-downloader loader，将自行编译"
fi

chmod +x "$APP_RESOURCES/runtime"/* 2>/dev/null || true
[ -f "$LOADER_PATH" ] && chmod +x "$LOADER_PATH" || true

rm -rf "$TEMP_RUNTIME"

# ---------- 准备 FFmpeg ----------
echo ""
echo "[4/8] 准备 FFmpeg..."
FFMPEG_DEST="$APP_RESOURCES/bundle/ffmpeg"

# 优先使用系统 FFmpeg
if command -v ffmpeg &> /dev/null; then
    FFMPEG_PATH=$(which ffmpeg)
    echo "  使用系统 FFmpeg: $FFMPEG_PATH (版本: $(ffmpeg -version 2>&1 | head -1))"
    
    cp "$FFMPEG_PATH" "$FFMPEG_DEST"
    chmod +x "$FFMPEG_DEST"
    
    # 也复制 ffprobe（可选）
    if command -v ffprobe &> /dev/null; then
        cp "$(which ffprobe)" "$APP_RESOURCES/bundle/ffprobe"
        chmod +x "$APP_RESOURCES/bundle/ffprobe"
    fi
else
    # 下载静态 FFmpeg
    if [ "$RUNTIME_ARCH" = "aarch64" ]; then
        FFMPEG_URL="$FFMPEG_URL_ARM64"
    else
        FFMPEG_URL="$FFMPEG_URL_X86_64"
    fi
    
    FFMPEG_ZIP="$CACHE_DIR/ffmpeg_${RUNTIME_ARCH}.zip"
    if [ ! -f "$FFMPEG_ZIP" ]; then
        echo "  下载: $FFMPEG_URL"
        wget -q --show-progress -O "$FFMPEG_ZIP" "$FFMPEG_URL" || {
            echo "WARNING: FFmpeg 下载失败，将继续构建但用户需自行安装 FFmpeg"
        }
    fi
    
    if [ -f "$FFMPEG_ZIP" ]; then
        unzip -qo "$FFMPEG_ZIP" -d "$CACHE_DIR/ffmpeg_extract/"
        FFMPEG_BIN=$(find "$CACHE_DIR/ffmpeg_extract" -name "ffmpeg" -type f | head -1)
        if [ -n "$FFMPEG_BIN" ]; then
            cp "$FFMPEG_BIN" "$FFMPEG_DEST"
            chmod +x "$FFMPEG_DEST"
            echo "  FFmpeg 已就绪"
        fi
        rm -rf "$CACHE_DIR/ffmpeg_extract"
    fi
fi

# ---------- 安装 Python 依赖 ----------
echo ""
echo "[5/8] 安装 Python 依赖..."
PIP_INSTALL_DIR="$BUILD_DIR/.pip_install"
rm -rf "$PIP_INSTALL_DIR"
mkdir -p "$PIP_INSTALL_DIR"

echo "  安装依赖包..."
/opt/homebrew/bin/pip3.13 install \
    --target="$PIP_INSTALL_DIR" \
    --no-deps \
    --no-cache-dir \
    PySide6==6.10.3 \
    PySide6-Fluent-Widgets==1.11.2 \
    qrcode==8.2 \
    protobuf==7.35.0 \
    httpx==0.28.1 \
    psutil==7.2.2 2>&1 | grep -v "^Requirement already satisfied" || true

# 复制 site-packages
SITE_PACKAGES_DEST="$APP_RESOURCES/runtime/site-packages"
rm -rf "$SITE_PACKAGES_DEST"
mkdir -p "$SITE_PACKAGES_DEST"
cp -r "$PIP_INSTALL_DIR"/* "$SITE_PACKAGES_DEST/"
rm -rf "$PIP_INSTALL_DIR"

echo "  已安装的包:"
ls "$SITE_PACKAGES_DEST" | tr '\n' ' '
echo ""

# ---------- 复制项目源代码 ----------
echo ""
echo "[6/8] 复制项目源代码..."
SCRIPT_DEST="$APP_RESOURCES/script"

# 清理并复制
rm -rf "$SCRIPT_DEST"
mkdir -p "$SCRIPT_DEST"

# 复制 src 目录
cp -r "$PROJECT_DIR/src/"* "$SCRIPT_DEST/"

# 编译 Python 源码为 .pyc（减小体积、加快启动）
echo "  编译 Python 源码..."
/opt/homebrew/bin/python3.13 -m compileall -q -b "$SCRIPT_DEST" 2>/dev/null || true
/opt/homebrew/bin/python3.13 -m compileall -q -b "$SITE_PACKAGES_DEST" 2>/dev/null || true

# 可选：删除 .py 源文件以减小体积（保留 .pyc）
# find "$SCRIPT_DEST" -name "*.py" ! -name "__init__.py" -delete
# find "$SITE_PACKAGES_DEST" -name "*.py" ! -name "__init__.py" -delete

# 清理不需要的资源文件（减小体积）
echo "  清理冗余资源..."
rm -rf "$SCRIPT_DEST/res/icon" 2>/dev/null || true
rm -rf "$SCRIPT_DEST/res/image" 2>/dev/null || true
rm -f "$SCRIPT_DEST/res/i18n/bili23.zh_CN.ts" 2>/dev/null || true
rm -f "$SCRIPT_DEST/res/i18n/bili23.zh_TW.ts" 2>/dev/null || true

# ---------- 创建启动脚本 ----------
echo ""
echo "[7/8] 创建启动器..."

# 主启动脚本（如果使用 bash 启动器）
cat > "$APP_MACOS/bili23-launcher" << 'SH_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_RESOURCES="$SCRIPT_DIR/../Resources"

export PYSTAND="$APP_RESOURCES/bili23-downloader"
export PYSTAND_HOME="$APP_RESOURCES"
export PYSTAND_RUNTIME="$APP_RESOURCES/runtime"
export PYSTAND_SCRIPT="$APP_RESOURCES/script/main.py"
export PYTHONUTF8=1
export PYTHONCOERCECLOCALE=1

cd "$APP_RESOURCES"

# 检查 FFmpeg
if [ ! -f "$APP_RESOURCES/bundle/ffmpeg" ]; then
    # 尝试系统 FFmpeg
    if command -v ffmpeg &> /dev/null; then
        export PATH="$APP_RESOURCES/bundle:$PATH"
    fi
else
    export PATH="$APP_RESOURCES/bundle:$PATH"
fi

exec "$APP_RESOURCES/bili23-downloader" "$@"
SH_EOF
chmod +x "$APP_MACOS/bili23-launcher"

# Python 入口包装脚本（如果 loader 不存在时备用）
cat > "$APP_MACOS/main" << 'MAIN_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_RESOURCES="$SCRIPT_DIR/../Resources"

export PYSTAND="$APP_RESOURCES/bili23-downloader"
export PYSTAND_HOME="$APP_RESOURCES"
export PYSTAND_RUNTIME="$APP_RESOURCES/runtime"
export PYSTAND_SCRIPT="$APP_RESOURCES/script/main.py"
export PYTHONUTF8=1
export PYTHONCOERCECLOCALE=1
export PYTHONHOME="$APP_RESOURCES/runtime"

cd "$APP_RESOURCES"

# 设置 FFmpeg 路径
export PATH="$APP_RESOURCES/bundle:$PATH"

if [ -x "$APP_RESOURCES/bili23-downloader" ]; then
    exec "$APP_RESOURCES/bili23-downloader" "$@"
elif [ -x "$APP_RESOURCES/runtime/python3.12" ]; then
    exec "$APP_RESOURCES/runtime/python3.12" -S "$APP_RESOURCES/script/main.py" "$@"
elif command -v python3 &> /dev/null; then
    echo "使用系统 Python 运行..."
    exec python3 "$APP_RESOURCES/script/main.py" "$@"
else
    echo "ERROR: 无法找到 Python 运行时" >&2
    exit 1
fi
MAIN_EOF
chmod +x "$APP_MACOS/main"

# ---------- 创建 Info.plist ----------
cat > "$BUILD_DIR/app_build/Contents/Info.plist" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>main</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleName</key>
    <string>bili23-AISum</string>
    <key>CFBundleDisplayName</key>
    <string>bili23-AISum</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>${MIN_MACOS}</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSRequiresNativeExecution</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
</dict>
</plist>
PLIST_EOF

# 复制应用图标
if [ -f "$PROJECT_DIR/assets/app.icns" ]; then
    cp "$PROJECT_DIR/assets/app.icns" "$APP_RESOURCES/app.icns"
    echo "  应用图标已复制"
else
    echo "  WARNING: assets/app.icns 不存在"
fi

# ---------- 生成依赖清单 ----------
echo ""
echo "  生成依赖清单..."
DEP_LOG="$BUILD_DIR/dependency_log_${RUNTIME_ARCH}.txt"
{
    echo "=============================================="
    echo "  bili23-AISum - 依赖清单"
    echo "  构建时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  版本: $VERSION_NAME"
    echo "  目标架构: $TARGET_ARCH"
    echo "  最低系统版本: macOS $MIN_MACOS"
    echo "=============================================="
    echo ""
    echo "--- 运行时 ---"
    echo "Python 静态运行时: $PYTHON_RUNTIME_URL"
    if [ -x "$FFMPEG_DEST" ]; then
        echo -n "FFmpeg: "
        "$FFMPEG_DEST" -version 2>&1 | head -1 || echo "已嵌入"
        echo "来源: 系统 FFmpeg ($(which ffmpeg))"
    else
        echo "FFmpeg: 未嵌入（需用户自行安装）"
    fi
    echo ""
    echo "--- pip 依赖 ---"
    pip3 list 2>/dev/null | grep -E "PySide6|httpx|qrcode|protobuf|psutil|QFluentWidgets" || true
    echo ""
    echo "--- 内嵌文件 ---"
    echo "loader: $([ -x "$LOADER_PATH" ] && echo 'bili23-downloader (Python静态链接Loader)' || echo 'bash启动器')"
    echo "FFmpeg: $([ -x "$FFMPEG_DEST" ] && echo '已嵌入' || echo '未嵌入')"
    echo "site-packages: $(du -sh "$SITE_PACKAGES_DEST" 2>/dev/null | cut -f1)"
    echo "script: $(du -sh "$SCRIPT_DEST" 2>/dev/null | cut -f1)"
    echo "runtime: $(du -sh "$APP_RESOURCES/runtime" 2>/dev/null | cut -f1)"
} > "$DEP_LOG"
echo "  依赖清单: $DEP_LOG"

# ---------- 打包 ----------
echo ""
echo "[8/8] 打包..."

DMG_NAME="${APP_NAME}_${VERSION_NAME}_macos_${TARGET_ARCH}.dmg"
DMG_PATH="$BUILD_DIR/$DMG_NAME"
ZIP_NAME="${APP_NAME}_${VERSION_NAME}_macos_${TARGET_ARCH}.zip"
ZIP_PATH="$BUILD_DIR/$ZIP_NAME"

# 清理旧文件
rm -f "$DMG_PATH" "$ZIP_PATH"

# 移动 app 到直接可用的位置
mv "$BUILD_DIR/app_build" "$BUILD_DIR/$APP_NAME.app"

# 尝试 DMG（可能因沙箱限制失败）
DMG_SUCCESS=false
if [ "$HAS_CREATE_DMG" = true ]; then
    echo "  使用 create-dmg 生成 DMG..."
    create-dmg \
        --volname "bili23-AISum Installer" \
        --window-pos 400 200 \
        --window-size 660 400 \
        --icon-size 80 \
        --icon "${APP_NAME}.app" 160 160 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 500 160 \
        "$DMG_PATH" \
        "$BUILD_DIR/$APP_NAME.app/" 2>/dev/null && DMG_SUCCESS=true
fi

if [ "$DMG_SUCCESS" = false ]; then
    # 尝试 hdiutil
    TEMP_DMG="$BUILD_DIR/temp.dmg"
    rm -f "$TEMP_DMG"
    
    APP_SIZE=$(du -sk "$BUILD_DIR/$APP_NAME.app" | cut -f1)
    DMG_SIZE=$((APP_SIZE * 15 / 10 + 20480))
    
    if hdiutil create -size ${DMG_SIZE}k -volname "bili23-AISum" -fs HFS+ -srcfolder "$BUILD_DIR/$APP_NAME.app" "$TEMP_DMG" 2>/dev/null; then
        if hdiutil convert "$TEMP_DMG" -format UDZO -o "$DMG_PATH" 2>/dev/null; then
            DMG_SUCCESS=true
        fi
        rm -f "$TEMP_DMG"
    fi
fi

# 无论如何都创建 zip（作为备选分发格式）
echo "  创建 ZIP 分发包..."
cd "$BUILD_DIR"
zip -qr "$ZIP_NAME" "$APP_NAME.app"
cd "$PROJECT_DIR"

if [ "$DMG_SUCCESS" = true ]; then
    echo ""
    echo "========================================"
    echo "  打包完成!"
    echo "  DMG 文件: $DMG_PATH"
    echo "  ZIP 文件: $ZIP_PATH"
    echo "  依赖清单: $DEP_LOG"
    echo "  文件大小: $(du -sh "$DMG_PATH" | cut -f1)"
else
    echo ""
    echo "========================================"
    echo "  打包完成!"
    echo "  App 捆绑包: $BUILD_DIR/$APP_NAME.app"
    echo "  ZIP 文件: $ZIP_PATH"
    echo "  依赖清单: $DEP_LOG"
    echo "  文件大小: $(du -sh "$ZIP_PATH" | cut -f1)"
    echo ""
    echo "  DMG 创建失败（可能因环境限制），可通过以下命令手动创建："
    echo "    hdiutil create -srcfolder \"$BUILD_DIR/$APP_NAME.app\" \"$DMG_PATH\""
fi
echo "========================================"

# ---------- 签名提示 ----------
echo ""
echo "--- 代码签名与公证指南 ---"
echo "本 DMG 未签名，在 macOS 上首次打开时需要右键 → 打开"
echo "如需正式分发签名，请执行:"
echo ""
echo "  # 1. 对 .app 签名"
echo "  codesign --force --deep --options runtime \\"
echo "    --sign \"Developer ID Application: Your Name (TEAMID)\" \\"
echo "    --entitlements entitlements.plist \\"
echo "    \"$BUILD_DIR/app_build\""
echo ""
echo "  # 2. 重新打包 DMG"
echo "  # (重新运行第 8 步)"
echo ""
echo "  # 3. 公证 DMG"
echo "  xcrun notarytool submit \"$DMG_PATH\" \\"
echo "    --apple-id your@email.com \\"
echo "    --team-id TEAMID \\"
echo "    --password @keychain:AC_PASSWORD \\"
echo "    --wait"
echo ""
echo "  # 4. 装订公证票据"
echo "  xcrun stapler staple \"$DMG_PATH\""
