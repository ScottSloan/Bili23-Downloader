"""
把构建好的前端挂上（S4）

部署形态下 WebUI 与后端是**同一个服务**：Docker 里只有一个容器，用户开
`http://host:23331` 就该看到界面，而不是一份 JSON。开发时才是 vite dev server
加代理那一套。

## 找不到构建产物不是错误

从源码跑后端时 `webui/dist` 常常还不存在（没跑过 `npm run build`）。那时后端应当
照常提供 API —— 前端开发用的是 vite dev server，本来也不需要这里挂的静态文件。
所以找不到就只记一句提示，不拦启动。

## history 模式要回落到 index.html

前端路由是 `createWebHistory`，`/download` 这种地址在服务端并没有对应的文件。
直接 404 的话，用户刷新任何非首页的地址都会看到 404 —— 必须回落到 `index.html`
由前端路由接管。

**但 `/api` 开头的绝不能回落**：那样一个拼错的接口地址会返回一份 HTML，
前端拿去 `JSON.parse` 得到的是「Unexpected token <」，排查起来要绕一大圈。
"""

from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# 相对仓库根：src/web/static.py → 上三级是仓库根
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "webui" / "dist"

def find_dist() -> Optional[Path]:
    """构建产物在哪。没有就返回 None"""
    index = DIST_DIR / "index.html"

    return DIST_DIR if index.is_file() else None

def mount(app: FastAPI, api_prefix: str = "/api") -> bool:
    """
    把前端挂到根路径上，返回是否挂上了

    **必须在所有 API 路由注册之后调用**：根路径的挂载会吃掉所有未匹配的路径，
    先挂的话 API 就再也轮不到了
    """
    dist = find_dist()

    if dist is None:
        logger.info(
            "未找到前端构建产物（%s），只提供 API。"
            "要在浏览器里打开界面，先在 webui/ 下执行 npm run build；"
            "开发时用 npm run dev 起 vite，它会把 /api 代理到这里",
            DIST_DIR)

        return False

    assets = dist / "assets"

    if assets.is_dir():
        # 带指纹的静态资源单独挂，交给 StaticFiles 处理 Range、缓存头这些
        app.mount("/assets", StaticFiles(directory = assets), name = "assets")

    index_file = dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema = False)
    async def spa_fallback(full_path: str):
        # API 路径绝不回落成 HTML，理由见模块说明
        if full_path.startswith(api_prefix.strip("/")):
            return JSONResponse({"detail": "Not Found", "code": "NOT_FOUND"}, status_code = 404)

        # dist 根下的真实文件（favicon、manifest 等）直接给
        candidate = dist / full_path

        if full_path and candidate.is_file():
            # 解析一次再比：`..` 与符号链接在这里同样能越界，
            # 这套判断与 web/paths.py 是同一个道理
            try:
                resolved = candidate.resolve()

                if resolved.is_relative_to(dist.resolve()):
                    return FileResponse(resolved)

            except (OSError, ValueError):
                pass

        return FileResponse(index_file)

    logger.info("已挂载前端：%s", dist)

    return True
