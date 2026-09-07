import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// 开发时 /api 与 /api/ws 都转发给后端（`python src/main.py --web-ui`）。
//
// S0 阶段这里连的是桌面版内置的 MCP 服务，还要从 config.json 里读一个 Bearer 令牌塞进去。
// S3 换成 FastAPI 之后那一整套没有了：**鉴权是 session cookie**，浏览器自己会带，
// 代理不需要也不应该插手。
//
// 走代理而不是让浏览器直连，是为了绕开 CORS —— 后端默认只听环回地址。
function backendPort(): number {
  if (process.env.BILI23_PORT) {
    return Number(process.env.BILI23_PORT)
  }

  // 端口存在共用的 config.json 里，读出来省得每个人手动配一遍。
  // 读不到就用默认值，不像 S0 那样直接把代理关掉 —— 那时是因为没有令牌就一定连不上，
  // 现在只是端口可能不对，试一下的代价很低
  try {
    const dir =
      process.platform === 'win32'
        ? process.env.APPDATA || path.join(homedir(), 'AppData', 'Roaming')
        : process.platform === 'darwin'
          ? path.join(homedir(), 'Library', 'Application Support')
          : process.env.XDG_DATA_HOME || path.join(homedir(), '.local', 'share')

    const file = path.join(dir, 'Bili23 Downloader', 'config.json')
    const webui = JSON.parse(readFileSync(file, 'utf-8')).WebUI || {}

    return Number(webui.webui_port) || 23331
  } catch {
    return 23331
  }
}

const target = process.env.BILI23_API || `http://127.0.0.1:${backendPort()}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    proxy: {
      '/api': {
        target,
        changeOrigin: true,
        // 事件推送走 /api/ws，不开这个的话 WebSocket 升级请求会被代理当成普通请求
        ws: true,
      },
    },
  },
})
