// 后端请求的统一入口
//
// 鉴权由 vite 代理注入（见 vite.config.js），前端不持有令牌。
// S3 换成 FastAPI + 密码鉴权后，这里改成带 credentials 的同源请求即可。

import { t } from '@/i18n'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)

    this.name = 'ApiError'
    this.status = status
  }
}

async function request(method, path, body) {
  let response

  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    // 桌面版没开、代理没配好都会落到这里，给一句能照着排查的提示
    throw new ApiError(t('error.backendUnreachable'), 0)
  }

  let payload = null

  try {
    payload = await response.json()
  } catch {
    // 后端在鉴权失败等分支下会返回空体
  }

  if (!response.ok) {
    throw new ApiError(
      payload?.error || t('error.requestFailed', { status: response.status }),
      response.status,
    )
  }

  return payload
}

export const api = {
  getStatus: () => request('GET', '/status'),
  getParseTree: () => request('GET', '/parse/tree'),
  parseUrl: (url) => request('POST', '/parse', { url }),
}
