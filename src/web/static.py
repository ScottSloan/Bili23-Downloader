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

## 缓存头必须自己设

`StaticFiles` 只给 `last-modified` 与 `etag`，**不给 `Cache-Control`**。少了它，浏览器
对 `index.html` 走的是**启发式缓存**（拿 `Last-Modified` 的年龄掐一个比例当新鲜期），
于是：

- `index.html` 里写死了带指纹的 JS 文件名。壳被缓存住，就等于整个前端被钉在旧版本上，
  **新功能上线后用户看到的仍是旧界面，而且没有任何报错** —— 表现成「这个按钮点了没反应」，
  查起来会一路怀疑到业务代码上去
- 反过来 `/assets` 下的文件名本身带内容指纹，改了内容就换名字，
  完全可以让浏览器永久缓存，却因为没有这个头每次都要回来问一次

所以两边各设各的：壳 `no-cache`，指纹资源 `immutable` 一年。

壳每次导航都会重新取一遍整份（**Starlette 的 `FileResponse` 不处理条件请求 ——
`If-None-Match` 回 304 的逻辑在 `StaticFiles` 里，这条回落路径用不上它**），
但那是 2.5 KB，而真正大的 JS / CSS 一年都不用再问一次。这笔账划算得很。
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

# 文件名带内容指纹，改了内容就换名字，可以放心让浏览器一直留着
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"

# 壳与 dist 根下那些不带指纹的文件（favicon、manifest）：每次都回来问一次。
# `no-cache` 不是「不缓存」，是「用之前必须先问服务端」
REVALIDATE_CACHE = "no-cache"

class ImmutableStaticFiles(StaticFiles):
    """给带指纹的资源补上 Cache-Control，StaticFiles 自己不设这个头"""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)

        response.headers["cache-control"] = IMMUTABLE_CACHE

        return response

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
        # 带指纹的静态资源单独挂，Range 交给 StaticFiles，缓存头由子类补
        app.mount("/assets", ImmutableStaticFiles(directory = assets), name = "assets")

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
                    return FileResponse(resolved,
                                        headers = {"cache-control": REVALIDATE_CACHE})

            except (OSError, ValueError):
                pass

        return FileResponse(index_file, headers = {"cache-control": REVALIDATE_CACHE})

    logger.info("已挂载前端：%s", dist)

    return True
