import { t } from '@/i18n'
import type { paths } from './schema'

/** 从生成的类型里取某个接口的成功响应体 */
export type Ok<P extends keyof paths, M extends keyof paths[P]> = paths[P][M] extends {
  responses: { 200: { content: { 'application/json': infer R } } }
}
  ? R
  : never

/** 取某个接口的请求体 */
export type Body<P extends keyof paths, M extends keyof paths[P]> = paths[P][M] extends {
  requestBody: { content: { 'application/json': infer B } }
}
  ? B
  : never

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)

    this.name = 'ApiError'
    this.status = status
  }

  /** 未登录。调用方一般不必自己处理，`onUnauthorized` 会统一接管 */
  get unauthorized(): boolean {
    return this.status === 401
  }
}

// 401 的统一处理。会话过期可能发生在任何一次请求上，让每个调用点各写一遍
// 「捕获 401 → 跳登录」既啰嗦又一定会漏掉几处
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

// 登录、查会话、健康检查本身不需要会话，它们返回 401 时不该触发「跳登录」——
// 否则在登录页输错密码会打断当前这一次交互。
//
// 改口令也在这里：它的 401 意思是「你填的旧口令不对」，会话本身是好的。
// 漏掉这一条的话，在设置页把旧口令敲错一次就会被踢回登录页
const NO_REDIRECT = new Set(['/auth/login', '/auth/session', '/auth/password', '/health'])

function buildUrl(path: string, query?: Record<string, unknown>): string {
  const url = `/api${path}`

  if (!query) {
    return url
  }

  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(query)) {
    // undefined / null 一律不发：后端多数参数有默认值，发一个空串反而会被当成显式取值
    if (value !== undefined && value !== null) {
      params.set(key, String(value))
    }
  }

  const text = params.toString()

  return text ? `${url}?${text}` : url
}

export interface RequestOptions {
  query?: Record<string, unknown>
  body?: unknown
  signal?: AbortSignal
}

export async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  let response: Response

  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers: options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      // 同源部署时是默认行为，写出来是为了在反向代理下换了域名也照常带 cookie
      credentials: 'same-origin',
      signal: options.signal,
    })
  } catch (error) {
    // 用户主动取消（切走页面、重新发起解析）不是错误，原样抛出去让调用方识别
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }

    throw new ApiError(t('error.backendUnreachable'), 0)
  }

  let payload: unknown = null

  try {
    payload = await response.json()
  } catch {
    // 204 与部分错误分支没有响应体
  }

  if (!response.ok) {
    if (response.status === 401 && !NO_REDIRECT.has(path) && onUnauthorized) {
      onUnauthorized()
    }

    throw new ApiError(errorMessage(payload, response.status), response.status)
  }

  return payload as T
}

function errorMessage(payload: unknown, status: number): string {
  const body = payload as { detail?: unknown; code?: unknown } | null

  const detail = body?.detail

  if (typeof body?.code === 'string' && body.code) {
    const key = `error.code.${body.code}`
    const text = t(key)

    if (text !== key) {
      return text
    }
  }

  if (typeof detail === 'string' && detail) {
    return detail
  }

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { loc?: unknown[]; msg?: string }

    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : ''

    return field ? `${field}: ${first.msg ?? ''}` : (first.msg ?? '')
  }

  return t('error.requestFailed', { status })
}

export const get = <T>(path: string, query?: Record<string, unknown>, signal?: AbortSignal) =>
  request<T>('GET', path, { query, signal })

export const post = <T>(
  path: string,
  body?: unknown,
  query?: Record<string, unknown>,
  signal?: AbortSignal,
) => request<T>('POST', path, { body, query, signal })

export const del = <T>(path: string, query?: Record<string, unknown>, signal?: AbortSignal) =>
  request<T>('DELETE', path, { query, signal })
