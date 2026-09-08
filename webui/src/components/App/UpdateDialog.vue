<script setup lang="ts">
/**
 * 有新版本
 *
 * 对应桌面版 `signal_bus.update.show_dialog` 拉起的那个对话框：版本号、更新说明、
 * 一个去下载的入口。
 *
 * **Web 端不做「跳过此版本」**。桌面版有那个选项（`config.skip_version`），
 * 是因为它每次启动都自动查、不跳过会天天弹。这边只在进页面时查一次且从不打断操作，
 * 多一个要记的状态不划算。
 */
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { useUpdateStore } from '@/stores/updateStore'
import { t } from '@/i18n'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const store = useUpdateStore()

function download() {
  if (store.updateUrl) {
    // noopener：打开的是外部页面，不该拿到我们这个窗口的引用
    window.open(store.updateUrl, '_blank', 'noopener')
  }

  emit('close')
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('update.title', { version: store.version })"
    width="560px"
    @close="emit('close')"
  >
    <template #hint>
      {{ t('update.from', { current: store.currentVersion, latest: store.version }) }}
      <span v-if="store.required" class="required">{{ t('update.required') }}</span>
    </template>

    <!-- 更新说明是服务端下发的多行纯文本，按原样排版；用 pre-wrap 而不是渲染
         markdown —— 内容来自外部服务，不该在这里跑一个解析器 -->
    <pre class="content">{{ store.content || t('update.noContent') }}</pre>

    <template #actions>
      <primaryPushButton :title="t('update.download')" @click="download" />
      <pushButton :title="t('update.later')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.required {
  margin-left: 8px;
  color: var(--text-danger);
}

.content {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 42vh;
  overflow-y: auto;
  margin: 0;
  padding: 10px 12px;
  border-radius: 5px;
  box-sizing: border-box;

  font: inherit;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;

  color: var(--text-primary);
  background-color: var(--card-fill-default);
  border: 1px solid var(--card-stroke-default);
}
</style>
