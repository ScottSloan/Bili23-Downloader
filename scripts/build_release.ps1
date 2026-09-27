<#
.SYNOPSIS
    构建带内嵌源码与完整性清单的发布目录。

.DESCRIPTION
    顺序是有讲究的：清单必须在 exe 就位之前生成 —— 它覆盖的是随包的其他文件，
    启动器自己没法算自己的哈希（清单就嵌在它的资源段里）。正因为清单不含 exe，
    整个流程只需要编译一次。

        1. 铺开 runtime 模板
        2. 打包应用源码为 app.zip（py + pyc）
        3. 扫描发布目录生成 manifest.bin
        4. 编译 exe，把两者一起嵌进资源段
        5. 放入 exe

    产出的是未签名的 exe，签名另做。

.EXAMPLE
    .\scripts\build_release.ps1 -RuntimeDir D:\Projects\runtime\windows_x64_runtime `
                                -OutputDir .\release
#>
[CmdletBinding()]
param(
    # 有默认值，不能再标 Mandatory —— 那样 PowerShell 只会报"缺少必需参数"，
    # 默认值永远轮不到生效
    #
    # 本脚本住在仓库的 scripts/ 下，所以上溯一级即仓库根
    [string]$SourceDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "src"),

    [Parameter(Mandatory)]
    [string]$RuntimeDir,

    [string]$OutputDir = ".\release",

    # 发布目录里启动器的文件名
    [string]$ExeName = "Bili23.exe",

    # 控制台子系统版本，调试用；正式发布应当用 GUI
    [switch]$Console,

    # 显式指定 cmake，留空则自动探测
    [string]$CMake,

    # 版本号，留空则从应用源码里读（那是唯一来源）
    [string]$AppVersion
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$work = Join-Path $root "build-release"

function Step([string]$text) {
    Write-Host "`n==> $text" -ForegroundColor Cyan
}

# ---------- 前置检查 ----------
foreach ($p in @($SourceDir, $RuntimeDir)) {
    if (-not (Test-Path -LiteralPath $p -PathType Container)) {
        throw "目录不存在：$p"
    }
}

if (-not $CMake) {
    $candidates = @(
        (Get-Command cmake -ErrorAction SilentlyContinue).Source
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
    )
    # 装在非默认盘时靠 vswhere 找
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $vs = & $vswhere -latest -products * -property installationPath
        if ($vs) {
            $candidates += Join-Path $vs "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
        }
    }
    $CMake = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $CMake) { throw "找不到 cmake，请用 -CMake 指定" }

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { throw "找不到 python" }

# 版本号只有一个来源：应用侧 config.py 里 APPConfig 的 app_version。
# resource.rc 与 manifest 都由 CMake 从这里注入 —— 之前三处各写各的，错过好几次
if (-not $AppVersion) {
    $configPy = Join-Path $SourceDir "util/common/config.py"
    if (-not (Test-Path -LiteralPath $configPy)) {
        throw "找不到版本号来源：$configPy（可用 -AppVersion 显式指定）"
    }
    # 前导空白要允许：app_version 是 APPConfig 的类属性，不在行首。
    # 匹配大小写并锚定行首，免得把 app_comparable_version 那一行也算进来
    $hit = Select-String -LiteralPath $configPy -CaseSensitive -Pattern '^\s*app_version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $hit) {
        throw "$configPy 里没找到 app_version"
    }
    $AppVersion = $hit.Matches[0].Groups[1].Value
}

Write-Host "cmake : $CMake" -ForegroundColor DarkGray
Write-Host "python: $python" -ForegroundColor DarkGray
Write-Host "版本  : $AppVersion" -ForegroundColor DarkGray

# ---------- 1. 铺开 runtime ----------
Step "准备发布目录"

if (Test-Path -LiteralPath $OutputDir) {
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
# 模板只提供 bundle、runtime、site-packages 与 LICENSE，启动器由本脚本编译后
# 放入（见第 5 步）。模板里不带 _pystand_static.int 这类入口脚本 —— 内嵌之后
# loader 也不再认它，磁盘上留着入口等于把那扇门重新打开：放一个同名文件就能
# 绕开内嵌源码，签过名的启动器又成了谁都能拿去跑任意代码的通用 loader
Copy-Item -LiteralPath $RuntimeDir -Destination $OutputDir -Recurse -Force

$OutputDir = (Resolve-Path -LiteralPath $OutputDir).Path
Write-Host "  $OutputDir"

# ---------- 2. 打包源码 ----------
Step "打包应用源码"

New-Item -ItemType Directory -Force -Path $work | Out-Null
$appZip = Join-Path $work "app.zip"
& $python (Join-Path $PSScriptRoot "build_app_zip.py") $SourceDir -o $appZip
if ($LASTEXITCODE -ne 0) { throw "打包源码失败" }

# ---------- 3. 生成清单 ----------
Step "生成完整性清单"

$manifest = Join-Path $work "manifest.bin"
& $python (Join-Path $PSScriptRoot "gen_manifest.py") $OutputDir -o $manifest --exclude $ExeName
if ($LASTEXITCODE -ne 0) { throw "生成清单失败" }

# ---------- 4. 编译 ----------
Step "编译启动器"

$buildDir = Join-Path $work "cmake"
$consoleFlag = if ($Console) { "ON" } else { "OFF" }

# 启动器自成一块，仓库根不再是 CMake 工程根
$launcherDir = Join-Path $root "launcher"

& $CMake -B $buildDir -S $launcherDir `
    "-DPYSTAND_CONSOLE=$consoleFlag" `
    "-DPYSTAND_EMBED_APP=ON" `
    "-DPYSTAND_APP_VERSION=$AppVersion" `
    "-DPYSTAND_APP_ZIP=$($appZip -replace '\\','/')" `
    "-DPYSTAND_MANIFEST_BIN=$($manifest -replace '\\','/')"
if ($LASTEXITCODE -ne 0) { throw "CMake 配置失败" }

& $CMake --build $buildDir --config Release
if ($LASTEXITCODE -ne 0) { throw "编译失败" }

$built = @(
    (Join-Path $buildDir "Release\PyStand.exe")
    (Join-Path $buildDir "PyStand.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $built) { throw "没有找到编译产物" }

# ---------- 5. 放入 exe ----------
Step "放入启动器"

$final = Join-Path $OutputDir $ExeName
Copy-Item -LiteralPath $built -Destination $final -Force
Write-Host ("  {0}  ({1:N1} KB)" -f $ExeName, ((Get-Item $final).Length / 1KB))

Write-Host "`n完成：$OutputDir" -ForegroundColor Green
