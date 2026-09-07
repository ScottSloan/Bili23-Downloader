<script setup lang="ts">
// 设置页
//
// 分两类：
//
// - **主题与强调色**只存在浏览器本地（D14：两端各存各的）。同一份 config.json 是
//   GUI 与 WebUI 共用的，主题跟着走的话，在手机上切一次深色会把桌面版也切了
// - **其余项**读写 `/api/settings`，与桌面版共用同一份配置
//
// 保存是自动的：改完就存，攒 400ms 合并成一次请求（见 settingsStore）。
// 没有「保存」按钮 —— 桌面版也没有，两边行为保持一致。

import { computed, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { useThemeStore } from '@/stores/themeStore'
import { t, setLocale } from '@/i18n'
import { SETTING_GROUPS, INTERFACE_ITEMS } from '@/components/App/settings/spec'
import settingRow from '@/components/App/settings/SettingRow.vue'
import settingCard from '@/components/Fluent/components/settings/SettingCard.vue'
import settingCardGroup from '@/components/Fluent/components/settings/SettingCardGroup.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'

const store = useSettingsStore()
const themeStore = useThemeStore()

const themeOptions = computed(() => [
  { value: 'light', label: t('settings.theme.light') },
  { value: 'dark', label: t('settings.theme.dark') },
  { value: 'auto', label: t('settings.theme.system') },
])

const restartNotice = computed(() =>
  store.pendingRestart.length
    ? t('settings.restartNotice', {
        items: store.pendingRestart.map((attr) => t(`settings.label.${attr}`)).join('、'),
      })
    : '',
)

onMounted(() => {
  void store.load()
})

// 离开设置页时把攒着的改动立刻发出去。少了这一步，改完最后一项就切页的话，
// 那 400ms 的合并窗口还没到，改动会跟着组件一起消失
onUnmounted(() => {
  void store.flush()
})

/** 语言要立刻反映到界面上，不能等下次刷新 */
function onChanged(attr: string, value: unknown) {
  if (attr === 'language') {
    setLocale(typeof value === 'string' ? value : null)
  }
}
</script>

<template>
  <div class="page-view">
    <p v-if="store.loading && !store.loaded" class="status">{{ t('settings.loading') }}</p>

    <p v-if="store.error" class="status error" role="alert">
      {{ t('settings.saveFailed', { message: store.error }) }}
    </p>

    <p v-if="restartNotice" class="status notice">{{ restartNotice }}</p>

    <settingCardGroup :title="t('settings.group.interface')">
      <settingCard
        :title="t('settings.theme.label')"
        :description="`${t('settings.theme.description')}（${t('settings.localOnly')}）`"
      >
        <comboBox
          :model-value="themeStore.mode"
          :options="themeOptions"
          :label="t('settings.theme.label')"
          @update:model-value="(value) => themeStore.setMode(String(value))"
        />
      </settingCard>

      <settingCard
        :title="t('settings.accent.label')"
        :description="`${t('settings.accent.description')}（${t('settings.localOnly')}）`"
      >
        <!-- 原生取色器：各平台自带的那个，比自己搭一个色轮可靠得多 -->
        <input
          type="color"
          class="color-input"
          :value="themeStore.primaryColor"
          :aria-label="t('settings.accent.label')"
          @input="themeStore.setPrimaryColor(($event.target as HTMLInputElement).value)"
        />
        <pushButton :title="t('settings.accent.reset')" @click="themeStore.setPrimaryColor('')" />
      </settingCard>

      <settingRow
        v-for="spec in INTERFACE_ITEMS"
        :key="spec.attr"
        :spec="spec"
        @changed="onChanged"
      />
    </settingCardGroup>

    <settingCardGroup
      v-for="group in SETTING_GROUPS"
      :key="group.key"
      :title="t(`settings.group.${group.key}`)"
    >
      <settingRow v-for="spec in group.items" :key="spec.attr" :spec="spec" @changed="onChanged" />
    </settingCardGroup>
  </div>
</template>

<style scoped>
.page-view {
  height: 100%;
  overflow-y: auto;
  padding: 15px 25px 40px 25px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.status.error {
  color: var(--text-danger);
}

.status.notice {
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--text-primary);
  background-color: var(--control-fill-secondary);
  border: 1px solid var(--card-stroke-default);
}

.color-input {
  width: 42px;
  height: 30px;
  padding: 2px;
  border-radius: 5px;
  cursor: pointer;
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
}
</style>
