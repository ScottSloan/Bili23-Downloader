<script setup lang="ts">
/**
 * 登录哔哩哔哩账号
 *
 * 版式照桌面版 `gui/dialog/login.py` 的 `LoginDialog`：**左边扫码、右边短信**，
 * 中间与两侧各留 40。左边是 160×160 的二维码加一行状态；右边从上到下是
 * 区号 + 手机号、验证码 + 「获取验证码」、登录按钮、「使用 Cookie 登录」链接。
 * 底部按钮区隐藏，点遮罩即可关闭（那边是 `buttonGroup.hide()` +
 * `setClosableOnMaskClicked(True)`）。
 *
 * **轮询由前端发起**（后端注释里写死了这条）：扫码是用户当面的动作，只有前端知道
 * 这个对话框还开不开着。服务端替它轮询的话，用户关掉页面之后循环还会一直跑。
 *
 * 三种方式共用一个成功出口 `finish()` —— 刷新账号信息、说一声、关掉。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import fluentComboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import cookieLoginDialog from './CookieLoginDialog.vue'
import { login, ApiError } from '@/api'
import { useAppStore } from '@/stores/appStore'
import { useToastStore } from '@/stores/toastStore'
import { runCaptcha } from './geetest'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const appStore = useAppStore()
const toast = useToastStore()

// ---------------- 扫码 ----------------

const qrSvg = ref('')
const qrKey = ref('')
/**
 * 二维码这一格现在是什么状态
 *
 * **取值直接用后端那套**（`QRCodeScanStatus` 的成员名小写：`waiting_for_scan` /
 * `waiting_for_confirmation` / `expired`），中间不再翻译一道 ——
 * 第一版自己起了 `waiting` / `scanned` 这样的名字，`scanned` 与后端的
 * `waiting_for_confirmation` 对不上，于是扫完码那一格的字始终不变，而且不报错。
 *
 * `loading` 与 `failed` 是本地才有的两个：那时候还没跟后端要到码
 */
const qrStatus = ref('loading')

let pollTimer: ReturnType<typeof setTimeout> | null = null

const qrHint = computed(() => t(`login.qrcode.${qrStatus.value}`))

function stopPolling() {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)

    pollTimer = null
  }
}

async function newQrcode() {
  stopPolling()

  qrStatus.value = 'loading'
  qrSvg.value = ''
  qrKey.value = ''

  try {
    const info = await login.qrcode()

    qrSvg.value = info.svg || ''
    qrKey.value = info.key
    qrStatus.value = 'waiting_for_scan'

    schedulePoll()
  } catch {
    qrStatus.value = 'failed'
  }
}

/**
 * 一秒问一次，与桌面版 `QRCode.start_polling` 的 QTimer 同一个节奏
 *
 * 用 setTimeout 递归而不是 setInterval：接口偶尔慢一两秒时，setInterval 会把请求叠起来
 */
function schedulePoll() {
  stopPolling()

  pollTimer = setTimeout(poll, 1000)
}

async function poll() {
  if (!props.open || !qrKey.value) {
    return
  }

  try {
    const status = await login.pollQrcode(qrKey.value)

    if (status.status === 'success') {
      // Cookie 在后端就地写好了，这里只要把用户信息取回来
      await finish(t('login.qrcode.success'))

      return
    }

    if (status.status === 'expired') {
      qrStatus.value = 'expired'

      // 过期了就别再问了，等用户点刷新
      return
    }

    // 其余状态原样记下（waiting_for_scan / waiting_for_confirmation）。
    // `unknown` 也照记 —— 文案里有兜底，总比停在上一个状态强
    qrStatus.value = status.status
  } catch {
    // 单次失败不改状态也不停下 —— 网络抖一下不该让二维码看起来失效了
  }

  schedulePoll()
}

// ---------------- 短信 ----------------

const regions = ref<{ value: string; label: string }[]>([])
const cid = ref('86')
const tel = ref('')
const code = ref('')
const captchaKey = ref('')
const smsSubmitting = ref(false)
const sending = ref(false)
const countdown = ref(0)

let countdownTimer: ReturnType<typeof setInterval> | null = null

const sendLabel = computed(() =>
  countdown.value > 0 ? t('login.sms.resend', { seconds: countdown.value }) : t('login.sms.send'),
)

function startCountdown() {
  // 与桌面版 SMSInfo.countdown 一致：60 秒
  countdown.value = 60

  countdownTimer = setInterval(() => {
    countdown.value -= 1

    if (countdown.value <= 0) {
      stopCountdown()
    }
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)

    countdownTimer = null
  }

  countdown.value = 0
}

async function loadRegions() {
  try {
    const payload = await login.smsRegions()

    // 字段名以 `util/common/data` 里那份表为准：`code` 是区号，`name` 是地区名。
    // 桌面版的 CidComboBox 显示 `+86`，这边把地区名也带上 —— 网页上有横向空间
    regions.value = (payload.regions || []).map((entry) => ({
      value: String(entry.code),
      label: `${entry.name} +${entry.code}`,
    }))
  } catch {
    // 拉不到就只留 +86，中国大陆的号码仍然能用
    regions.value = [{ value: '86', label: '中国大陆 +86' }]
  }
}

async function sendCode() {
  if (sending.value || countdown.value > 0) {
    return
  }

  if (!tel.value.trim()) {
    toast.error(t('login.sms.telEmpty'))

    return
  }

  sending.value = true

  try {
    const captcha = await login.smsCaptcha()

    // 滑块在浏览器里过。用户中途关掉会 reject 一个空错误，那时静默收场
    const result = await runCaptcha(captcha.gt, captcha.challenge)

    const sent = await login.smsSend({
      cid: cid.value,
      tel: tel.value.trim(),
      token: captcha.token,
      challenge: result.challenge,
      validate: result.validate,
      seccode: result.seccode,
    })

    captchaKey.value = sent.captcha_key

    startCountdown()

    toast.success(t('login.sms.sent'))
  } catch (e) {
    if (e instanceof Error && !e.message) {
      // 用户自己关掉了滑块
      return
    }

    if (e instanceof Error && e.message === 'geetest') {
      toast.error(t('login.sms.captchaFailed'), t('login.sms.captchaFailedDetail'))

      return
    }

    toast.error(t('login.sms.sendFailed'), e instanceof ApiError ? e.message : String(e))
  } finally {
    sending.value = false
  }
}

async function smsLogin() {
  if (smsSubmitting.value) {
    return
  }

  if (!tel.value.trim()) {
    toast.error(t('login.sms.telEmpty'))

    return
  }

  if (!code.value.trim()) {
    toast.error(t('login.sms.codeEmpty'))

    return
  }

  if (!captchaKey.value) {
    // captcha_key 是「发短信」那一步的返回值，没发过就登不了
    toast.error(t('login.sms.needSend'))

    return
  }

  smsSubmitting.value = true

  try {
    await login.smsVerify({
      cid: cid.value,
      tel: tel.value.trim(),
      code: code.value.trim(),
      captcha_key: captchaKey.value,
    })

    await finish(t('login.sms.success'))
  } catch (e) {
    toast.error(t('login.sms.failed'), e instanceof ApiError ? e.message : String(e))
  } finally {
    smsSubmitting.value = false
  }
}

// ---------------- Cookie ----------------

const cookieOpen = ref(false)

async function onCookieSuccess() {
  cookieOpen.value = false

  await finish(t('login.cookie.success'))
}

// ---------------- 共用 ----------------

async function finish(message: string) {
  stopPolling()
  stopCountdown()

  // refresh = true：顺带把 wbi 签名密钥刷新一遍，解析立刻就能用
  await appStore.fetchAccount(true)

  toast.success(message)

  emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      tel.value = ''
      code.value = ''
      captchaKey.value = ''

      stopCountdown()

      void newQrcode()

      if (!regions.value.length) {
        void loadRegions()
      }
    } else {
      // 对话框一关就把轮询停掉。留着的话用户切到别的页面，它还在一秒一次地问
      stopPolling()
      stopCountdown()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopPolling()
  stopCountdown()
})
</script>

<template>
  <fluentDialog :open="open" :title="t('login.title')" width="760px" @close="emit('close')">
    <div class="login">
      <!-- 左：扫码 -->
      <section class="pane qrcode-pane">
        <h3 class="section-title">{{ t('login.qrcode.title') }}</h3>

        <!-- 白底是必须的：二维码是纯黑路径，深色主题下直接贴上去扫不出来 -->
        <div class="qrcode" :class="{ 'is-expired': qrStatus === 'expired' }">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-if="qrSvg" class="qrcode-image" v-html="qrSvg" />
          <span v-else class="qrcode-loading" aria-hidden="true" />

          <button
            v-if="qrStatus === 'expired' || qrStatus === 'failed'"
            type="button"
            class="qrcode-refresh"
            @click="newQrcode"
          >
            {{ t('login.qrcode.refresh') }}
          </button>
        </div>

        <p class="qrcode-hint">{{ qrHint }}</p>
      </section>

      <!-- 右：短信 -->
      <section class="pane sms-pane">
        <h3 class="section-title">{{ t('login.sms.title') }}</h3>

        <div class="row">
          <fluentComboBox
            class="region"
            :model-value="cid"
            :options="regions"
            :label="t('login.sms.region')"
            @update:model-value="(value: string | number) => (cid = String(value))"
          />

          <lineEdit
            v-model="tel"
            class="grow"
            :placeholder="t('login.sms.tel')"
            :aria-label="t('login.sms.tel')"
          />
        </div>

        <div class="row">
          <lineEdit
            v-model="code"
            class="grow"
            :placeholder="t('login.sms.code')"
            :aria-label="t('login.sms.code')"
            @submit="smsLogin"
          />

          <button
            type="button"
            class="link send"
            :disabled="sending || countdown > 0"
            @click="sendCode"
          >
            {{ sendLabel }}
          </button>
        </div>

        <primaryPushButton
          class="submit"
          :title="smsSubmitting ? t('login.sms.submitting') : t('login.sms.submit')"
          :disabled="smsSubmitting"
          @click="smsLogin"
        />

        <button type="button" class="link" @click="cookieOpen = true">
          {{ t('login.cookie.entry') }}
        </button>
      </section>
    </div>

    <cookieLoginDialog
      :open="cookieOpen"
      @close="cookieOpen = false"
      @success="onCookieSuccess"
    />
  </fluentDialog>
</template>

<style scoped>
/* 两栏之间与两侧各 40，与桌面版 login_layout 的 addSpacing(40) 一致 */
.login {
  display: flex;
  flex-direction: row;
  gap: 40px;
  padding: 16px 40px 24px 40px;
}

.pane {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  min-width: 0;
}

/*
  **两栏不能平分。** 左边只有一张 160 的二维码，平分之后它空着一大半，
  而右边的手机号输入框被挤到 147 —— 一个手机号都摆不下。
  左边按内容定宽，剩下的全给短信那一栏
*/
.qrcode-pane {
  flex: 0 0 auto;
  width: 200px;
}

.sms-pane {
  flex: 1 1 auto;
}

/* SectionLabel，桌面版是 16px 加粗 */
.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ---- 扫码 ---- */

.qrcode {
  position: relative;
  width: 160px;
  height: 160px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  padding: 8px;
  box-sizing: border-box;
  /* 二维码本身是纯黑路径，底必须是白的 —— 深色主题下也一样 */
  background-color: #ffffff;
}

.qrcode-image {
  width: 100%;
  height: 100%;
  display: flex;
}

.qrcode-image :deep(svg) {
  width: 100%;
  height: 100%;
}

/* 过期时把码压暗，让「点击刷新」看得清 —— 与桌面版一样，过期的码不该还清晰可扫 */
.qrcode.is-expired .qrcode-image {
  opacity: 0.15;
}

.qrcode-loading {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid rgba(0, 0, 0, 0.12);
  border-top-color: var(--primary-color);
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.qrcode-refresh {
  position: absolute;
  font: inherit;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 5px;
  cursor: pointer;
  border: none;
  color: var(--text-on-accent);
  background-color: var(--primary-color);
}

.qrcode-hint {
  margin: 0;
  min-height: 20px;
  font-size: 14px;
  text-align: center;
  color: var(--text-secondary);
}

/* ---- 短信 ---- */

.sms-pane {
  justify-content: center;
  gap: 12px;
}

.sms-pane .row :deep(input) {
  /* <input> 有个约 20 字符的固有宽度，不写这句它在 flex 里不肯缩，
     反过来把区号下拉挤变形 */
  min-width: 0;
  width: 100%;
}

.row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.region {
  flex: 0 0 auto;
  min-width: 132px;
}

.grow {
  flex: 1 1 auto;
  min-width: 0;
}

.submit {
  /* 桌面版 setFixedWidth(175) */
  width: 175px;
  margin-top: 3px;
}

/* HyperlinkButton：主题色、无边框、悬停加下划线 */
.link {
  font: inherit;
  font-size: 14px;
  margin: 0;
  padding: 4px 6px;
  border: none;
  background: none;
  cursor: pointer;
  white-space: nowrap;
  color: var(--primary-color);
}

.link:hover:not(:disabled) {
  text-decoration: underline;
}

.link:disabled {
  cursor: default;
  color: var(--text-disabled);
}

.send {
  flex: 0 0 auto;
  min-width: 96px;
  text-align: center;
}

/* 窄屏上两栏叠成上下 */
@media (max-width: 700px) {
  .login {
    flex-direction: column;
    padding: 12px 20px 20px 20px;
    gap: 24px;
  }
}
</style>
