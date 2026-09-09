/**
 * 极验滑块
 *
 * 短信登录必须先过极验。桌面版为此起了一个本地 HTTP 服务（`util/auth/server.py`，
 * 端口 2333），把 `src/res/html/captcha.html` 用系统浏览器打开，用户过完再回传 ——
 * **因为极验的 JS 只跑在网页环境里**，Qt 那边没别的办法。
 *
 * WebUI 本身就是网页，不需要那一圈：直接在页面里初始化，拿到结果就发短信。
 *
 * ## 那个 gt.js 从极验的 CDN 加载
 *
 * `captcha.html` 里内联的那一大段就是极验官方的 `gt.js`（v0.4.8），它的作用只是
 * 去 `api.geetest.com` 问一下类型、再从 `static.geetest.com` 拉真正的验证码脚本。
 * **也就是说这套东西离开极验的服务器本来就不能用**，把加载器打进自己的包里
 * 换不来任何离线能力，只是多维护一份几百行的第三方代码。所以按需从 CDN 拉。
 *
 * 拉不到时抛错，由调用方提示用户 —— 这时短信登录走不通，扫码与 Cookie 还能用。
 */

const GT_SCRIPT = 'https://static.geetest.com/static/js/gt.0.4.9.js'

/** 极验回调里那三个值，发短信那一步要原样带回后端 */
export interface CaptchaResult {
  challenge: string
  validate: string
  seccode: string
}

interface GeetestObject {
  appendTo(selector: string | HTMLElement): void
  verify(): void
  onReady(handler: () => void): void
  onSuccess(handler: () => void): void
  onError(handler: (error: unknown) => void): void
  onClose(handler: () => void): void
  getValidate(): {
    geetest_challenge: string
    geetest_validate: string
    geetest_seccode: string
  }
}

declare global {
  interface Window {
    initGeetest?: (
      config: Record<string, unknown>,
      callback: (captcha: GeetestObject) => void,
    ) => void
  }
}

let loading: Promise<void> | null = null

function loadScript(): Promise<void> {
  if (window.initGeetest) {
    return Promise.resolve()
  }

  // 并发点两次「获取验证码」不该插两个 script 标签
  if (loading) {
    return loading
  }

  loading = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')

    script.src = GT_SCRIPT
    script.async = true

    script.onload = () => {
      loading = null

      if (window.initGeetest) {
        resolve()
      } else {
        reject(new Error('geetest'))
      }
    }

    script.onerror = () => {
      // 失败之后要能重试：不清掉的话这个 Promise 会一直是那个 rejected 的
      loading = null

      script.remove()

      reject(new Error('geetest'))
    }

    document.head.appendChild(script)
  })

  return loading
}

/**
 * 弹出滑块，过完返回那三个值
 *
 * 用 `product: 'bind'`：这个模式下极验不渲染任何按钮，由我们调 `verify()` 直接弹窗。
 * `captcha.html` 里用的是 `popup` —— 那种要先出现一个「点击进行验证」的按钮再点一次，
 * 而这边用户已经点过「获取验证码」了，再让他点一次没有道理。
 *
 * 用户关掉滑块时 reject 一个不带消息的错误，调用方据此静默收场 ——
 * 那是他自己取消的，不该弹一句「验证失败」
 */
export async function runCaptcha(gt: string, challenge: string): Promise<CaptchaResult> {
  await loadScript()

  return new Promise<CaptchaResult>((resolve, reject) => {
    window.initGeetest!(
      {
        gt,
        challenge,
        // 与 captcha.html 里那四个必填项一致
        offline: false,
        new_captcha: true,
        product: 'bind',
        https: true,
      },
      (captcha) => {
        captcha.onReady(() => captcha.verify())

        captcha.onSuccess(() => {
          const result = captcha.getValidate()

          resolve({
            challenge: result.geetest_challenge,
            validate: result.geetest_validate,
            seccode: result.geetest_seccode,
          })
        })

        captcha.onError((error) => reject(error instanceof Error ? error : new Error('geetest')))

        captcha.onClose(() => reject(new Error()))
      },
    )
  })
}
