"""
从 OpenAPI 生成前端的 TypeScript 类型（S3-12 / D3）

    .venv/Scripts/python.exe scripts/gen_api_types.py
    .venv/Scripts/python.exe scripts/gen_api_types.py --check   # 只校验是否为最新，不写文件

产物：

- `webui/src/api/openapi.json` —— 规格本身，纳入版本控制，改了接口能在 diff 里看见
- `webui/src/api/schema.d.ts`  —— openapi-typescript 生成的类型

## 不起服务器

FastAPI 的 `app.openapi()` 是纯计算，导入应用对象就能拿到。起一个真服务器再去 curl
既慢又要占端口，而且**会连带把 aria2 拉起来** —— 生成类型不该有这种副作用，
所以这里用 `create_app(with_aria2 = False)`。

## 数据目录必须隔离

导入 config 会按 `BILI23_DATA_DIR` 定位数据目录，不设的话会读写用户真实的 `config.json`
（首次运行还会往里写一个随机的 WebUI 口令）。生成类型这种事绝不该碰用户数据，
所以脚本一进来就把它指到临时目录。

## --check 干什么

给 CI 与提交前用：**接口改了却忘了重新生成**，前端拿到的类型就是旧的，
而 TypeScript 会信以为真 —— 那种错要到运行时才暴露。有了 --check 就能在合并前拦住。
"""

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent

SRC = ROOT / "src"
OUT_DIR = ROOT / "webui" / "src" / "api"

SPEC_FILE = OUT_DIR / "openapi.json"
TYPES_FILE = OUT_DIR / "schema.d.ts"

# 与 requirements-web.txt 里的版本无关：这是前端的工具链，用 npx 按需拉取。
# 固定大版本，避免哪天上游改了输出格式导致 --check 无故失败
OPENAPI_TYPESCRIPT = "openapi-typescript@7"

def build_spec() -> dict:
    """导入应用对象直接取规格，不起服务器"""
    sys.path.insert(0, str(SRC))

    # 必须赶在导入 config 之前设好，理由见模块说明
    os.environ.setdefault("BILI23_DATA_DIR", tempfile.mkdtemp(prefix = "bili23-openapi-"))

    try:
        from web.app import create_app

    except ImportError as e:
        print(f"导入后端失败：{e}", file = sys.stderr)
        print("WebUI 的依赖没装齐，先跑：pip install -r requirements-web.txt", file = sys.stderr)

        raise SystemExit(1)

    return create_app(with_aria2 = False).openapi()

def dump_spec(spec: dict) -> str:
    # 排序键 + 固定缩进：不这么做的话，每次生成的字典顺序都可能不同，
    # diff 里全是噪音，--check 也永远不会通过
    return json.dumps(spec, ensure_ascii = False, indent = 2, sort_keys = True) + "\n"

def run_openapi_typescript(spec_path: Path) -> str:
    npx = shutil.which("npx")

    if not npx:
        print("找不到 npx，无法生成 TypeScript 类型（Node.js 未安装或不在 PATH 中）",
              file = sys.stderr)

        raise SystemExit(1)

    result = subprocess.run(
        [npx, "--yes", OPENAPI_TYPESCRIPT, str(spec_path)],
        capture_output = True, text = True, encoding = "utf-8", cwd = str(ROOT / "webui"))

    if result.returncode != 0:
        print("openapi-typescript 执行失败：", file = sys.stderr)
        print(result.stderr[-2000:], file = sys.stderr)

        raise SystemExit(1)

    return result.stdout

def main() -> int:
    parser = argparse.ArgumentParser(description = "从 OpenAPI 生成前端 TypeScript 类型")
    parser.add_argument("--check", action = "store_true",
                        help = "只校验产物是否为最新，不写文件；不一致时退出码为 1")

    args = parser.parse_args()

    spec_text = dump_spec(build_spec())

    OUT_DIR.mkdir(parents = True, exist_ok = True)

    # 类型是从规格生成的，所以要先有一份规格文件给 openapi-typescript 读。
    # --check 模式下写到临时位置，绝不动工作区
    if args.check:
        with tempfile.TemporaryDirectory(prefix = "bili23-spec-") as tmp:
            probe = Path(tmp) / "openapi.json"
            probe.write_text(spec_text, encoding = "utf-8")

            types_text = run_openapi_typescript(probe)

    else:
        SPEC_FILE.write_text(spec_text, encoding = "utf-8")

        types_text = run_openapi_typescript(SPEC_FILE)

    if args.check:
        stale = []

        if not SPEC_FILE.is_file() or SPEC_FILE.read_text(encoding = "utf-8") != spec_text:
            stale.append(SPEC_FILE)

        if not TYPES_FILE.is_file() or TYPES_FILE.read_text(encoding = "utf-8") != types_text:
            stale.append(TYPES_FILE)

        if stale:
            print("接口类型已过期，请重新生成：", file = sys.stderr)

            for path in stale:
                print(f"  {path.relative_to(ROOT)}", file = sys.stderr)

            print("\n  .venv/Scripts/python.exe scripts/gen_api_types.py", file = sys.stderr)

            return 1

        print("接口类型是最新的")

        return 0

    TYPES_FILE.write_text(types_text, encoding = "utf-8")

    paths = len(json.loads(spec_text).get("paths", {}))

    print(f"已生成 {paths} 个接口的类型")
    print(f"  {SPEC_FILE.relative_to(ROOT)}")
    print(f"  {TYPES_FILE.relative_to(ROOT)}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
