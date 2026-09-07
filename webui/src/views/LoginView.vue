<script setup lang="ts">
// 进 WebUI 本身的登录页（D6：单用户 + 口令）
//
// **不是 B 站账号的登录** —— 那个在设置页里，两者的措辞要分清，
// 否则用户会以为在这里退出会把 B 站账号也退掉。
//
// 首次启动的口令是后端随机生成、只打印到控制台一次的（不入日志文件），
// 所以这里要给一句提示，不然用户会对着输入框发愣。

import { nextTick, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { t } from '@/i18n'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'

const authStore = useAuthStore()

const username = ref('admin')
const password = ref('')
const passwordInput = ref<InstanceType<typeof lineEdit> | null>(null)

onMounted(async () => {
  // 用户名多数时候就是默认的 admin，光标直接落到口令上
  await nextTick()

  passwordInput.value?.$el?.querySelector('input')?.focus()
})

async function submit() {
  if (!password.value || authStore.submitting) {
    return
  }

  if (await authStore.login(username.value, password.value)) {
    // 登录成功后 App.vue 会换成主界面，路由停在原处 ——
    // 会话过期前在哪一页，重新登录后还在哪一页
    password.value = ''
  }
}
</script>

<template>
  <div class="login-view">
    <form class="card" @submit.prevent="submit">
      <h1 class="title">{{ t('auth.title') }}</h1>
      <p class="hint">{{ t('auth.hint') }}</p>

      <label class="field">
        <span>{{ t('auth.username') }}</span>
        <lineEdit v-model="username" autocomplete="username" />
      </label>

      <label class="field">
        <span>{{ t('auth.password') }}</span>
        <lineEdit
          ref="passwordInput"
          v-model="password"
          type="password"
          autocomplete="current-password"
        />
      </label>

      <p v-if="authStore.error" class="error" role="alert">{{ authStore.error }}</p>

      <primaryPushButton
        :title="authStore.submitting ? t('auth.submitting') : t('auth.submit')"
        type="submit"
        :disabled="authStore.submitting || !password"
      />
    </form>
  </div>
</template>

<style scoped>
.login-view {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--solid-bg-base);
}

.card {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 28px 24px;
  border-radius: 8px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--text-primary);
}

.error {
  margin: 0;
  font-size: 12px;
  /* 用语义色而不是写死红色：深浅两套主题下的对比度不一样 */
  color: var(--text-danger);
}
</style>
