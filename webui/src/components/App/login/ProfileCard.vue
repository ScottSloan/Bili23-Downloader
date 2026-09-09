<script setup lang="ts">
/**
 * 已登录时点头像弹出的那张卡片
 *
 * 对应桌面版 `gui/component/profile.py` 的 `ProfileCard`（一个 Flyout）：
 * 头像、用户名、UID，下面两个链接 ——「个人空间」与「退出登录」。
 * 尺寸也照它：260×90，头像直径 48（`setRadius(24)`）。
 *
 * **退出前要确认**，桌面版那边是一个 MessageBox，措辞里点明「会清除本地保存的 Cookie」。
 *
 * 浮层贴着头像右边弹出（桌面版是 `FlyoutAnimationType.SLIDE_RIGHT`）。
 * 位置在挂载时按目标元素算一次，然后 teleport 到 body ——
 * 留在导航栏里会被它的 `overflow` 裁掉。
 *
 * 进场动画照 `SlideRightFlyoutAnimationManager`：位置与透明度两条并行动画，
 * **187ms、OutQuad**，从终点左边 8px 处滑过来，同时 0 → 1 淡入。
 * 退场那边没有动画（Flyout 是直接 close 的），这里也不做。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/appStore'
import { useToastStore } from '@/stores/toastStore'
import { login } from '@/api'
import { NOFACE_URL } from './noface'
import { t } from '@/i18n'

const props = defineProps<{
  /** 头像元素，浮层贴着它右边 */
  anchor: HTMLElement | null
}>()

const emit = defineEmits<{
  close: []
}>()

const appStore = useAppStore()
const toast = useToastStore()

const position = ref({ left: 0, top: 0 })
const confirming = ref(false)

function place() {
  if (!props.anchor) {
    return
  }

  const rect = props.anchor.getBoundingClientRect()

  // 贴右边，垂直居中对齐；再夹一下，别顶出屏幕
  const top = Math.min(
    Math.max(8, rect.top + rect.height / 2 - 45),
    Math.max(8, window.innerHeight - 98),
  )

  position.value = { left: rect.right + 8, top }
}

function onPointerDown(event: PointerEvent) {
  const target = event.target as Node

  if (props.anchor?.contains(target)) {
    // 点头像本身由头像那边处理开关，这里放过，否则会「关掉又立刻打开」
    return
  }

  if (!(target instanceof Element) || !target.closest('.profile-card')) {
    emit('close')
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  place()

  window.addEventListener('pointerdown', onPointerDown, true)
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', place)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onPointerDown, true)
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', place)
})

function openProfile() {
  if (appStore.uid) {
    window.open(`https://space.bilibili.com/${appStore.uid}`, '_blank', 'noopener')
  }

  emit('close')
}

async function confirmLogout() {
  try {
    await login.logout()

    await appStore.fetchAccount()

    toast.success(t('login.logout.done'))
  } catch {
    toast.error(t('login.logout.failed'))
  }

  emit('close')
}
</script>

<template>
  <teleport to="body">
    <div
      class="profile-card"
      role="dialog"
      :style="{ left: `${position.left}px`, top: `${position.top}px` }"
    >
      <template v-if="!confirming">
        <!-- 拿不到头像时用 B 站那张默认的，与导航栏那枚同源 -->
        <img
          class="face"
          :src="appStore.faceUrl || NOFACE_URL"
          :alt="t('user.avatarAlt')"
          referrerpolicy="no-referrer"
        />

        <div class="info">
          <div class="uname" :title="appStore.uname">{{ appStore.uname }}</div>
          <div class="uid">UID: {{ appStore.uid }}</div>

          <div class="links">
            <button type="button" class="link" @click="openProfile">
              {{ t('login.profile') }}
            </button>
            <button type="button" class="link" @click="confirming = true">
              {{ t('login.logout.entry') }}
            </button>
          </div>
        </div>
      </template>

      <!-- 退出要确认：它会连本地存的 Cookie 一起清掉，与桌面版那句话一致 -->
      <div v-else class="confirm">
        <p class="confirm-text">{{ t('login.logout.confirm') }}</p>

        <div class="links">
          <button type="button" class="link danger" @click="confirmLogout">
            {{ t('login.logout.yes') }}
          </button>
          <button type="button" class="link" @click="confirming = false">
            {{ t('settings.dialog.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
/* 260×90，与桌面版 setFixedSize 一致 */
.profile-card {
  position: fixed;
  z-index: 90;
  box-sizing: border-box;
  width: 260px;
  min-height: 90px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;

  color: var(--text-primary);
  background-color: var(--flyout-fill);
  border: 1px solid var(--flyout-stroke);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);

  /* 向右滑出 + 淡入，187ms OutQuad，见文件开头 */
  animation: flyout-slide-right 187ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/*
  只写 from：to 就是元素自己的静止状态。这样位置由 :style 的 left/top 定，
  动画只负责那 8px 的位移，两者不会打架
*/
@keyframes flyout-slide-right {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .profile-card {
    animation: none;
  }
}

.face {
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}


.info {
  flex: 1 1 auto;
  min-width: 0;
}

.uname {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.uid {
  font-size: 12px;
  color: var(--text-secondary);
}

.links {
  display: flex;
  flex-direction: row;
  gap: 4px;
  margin-top: 2px;
}

.confirm {
  flex: 1 1 auto;
}

.confirm-text {
  margin: 0 0 6px 0;
  font-size: 13px;
  line-height: 1.5;
}

.link {
  font: inherit;
  font-size: 13px;
  margin: 0;
  padding: 2px 4px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--primary-color);
}

.link:hover {
  text-decoration: underline;
}

.link.danger {
  color: var(--text-danger);
}
</style>
