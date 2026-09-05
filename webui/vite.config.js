import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// S0 阶段后端借用桌面版内置的 MCP HTTP 服务，鉴权沿用它的 Bearer 令牌。
// 令牌就在本机的 config.json 里，直接读出来省得每个人手动配一遍环境变量。
// S3 换成 FastAPI + 密码鉴权之后，这一整段删掉。
function appDataDir() {
  if (process.platform === 'win32') {
    return process.env.APPDATA || path.join(homedir(), 'AppData', 'Roaming')
  }

  if (process.platform === 'darwin') {
    return path.join(homedir(), 'Library', 'Application Support')
  }

  return process.env.XDG_DATA_HOME || path.join(homedir(), '.local', 'share')
}

function readBackend() {
  // 显式指定的环境变量优先，方便连别的机器上的实例
  if (process.env.BILI23_TOKEN) {
    return {
      token: process.env.BILI23_TOKEN,
      target: process.env.BILI23_API || 'http://127.0.0.1:23330',
    }
  }

  try {
    const file = path.join(appDataDir(), 'Bili23 Downloader', 'config.json')
    const mcp = JSON.parse(readFileSync(file, 'utf-8')).MCP || {}

    if (!mcp.mcp_token) {
      return null
    }

    return {
      token: mcp.mcp_token,
      target: `http://127.0.0.1:${mcp.mcp_port || 23330}`,
    }
  } catch {
    return null
  }
}

const backend = readBackend()

if (!backend) {
  console.warn(
    '\n[bili23] 未能读到 MCP 令牌，/api 代理不可用。\n' +
      '         请先在桌面版的「设置 → MCP」里启用服务并启动程序，或设置 BILI23_TOKEN 环境变量。\n',
  )
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    proxy: backend
      ? {
          // 走代理而不是让浏览器直连：既绕开 CORS，也不必把令牌暴露到前端代码里。
          // MCP 服务器只绑 127.0.0.1，且会校验 Origin，浏览器本来也直连不上
          '/api': {
            target: backend.target,
            changeOrigin: true,
            configure(proxy) {
              proxy.on('proxyReq', (proxyReq) => {
                proxyReq.setHeader('Authorization', `Bearer ${backend.token}`)
                // 代理转发时不要带上浏览器的 Origin，否则会被服务端的来源校验拦下
                proxyReq.removeHeader('origin')
              })
            },
          },
        }
      : undefined,
  },
})
