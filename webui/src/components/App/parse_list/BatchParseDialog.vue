<script setup lang="ts">
/**
 * 批量解析
 *
 * 对应桌面版 `gui/dialog/misc/batch_parse.py`：一行一条链接，只认 av / BV。
 *
 * ## 与桌面版的架构差异
 *
 * 桌面版把整批链接交给 `DynamicParser`，由它在一个后台线程里顺序解析并往同一棵树上
 * 追加节点。Web 端**改成前端逐条调 `/api/parse`**：
 *
 * - 那个接口已经在用、已经有测试，不必为批量再开一条服务端链路
 * - 进度与「中途停下」在前端天然就有；做成一个长请求的话，二十条链接要等几十秒，
 *   期间没有任何反馈，还容易撞上网关超时
 *
 * 代价是每条链接的结果各自成为一个顶层节点，而不是像桌面版那样收在一个动态节点下面。
 */
import { computed, ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentCheckBox from '@/components/Fluent/components/widgets/checkbox/TransparentCheckBox.vue'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
  /** 「解析完每条链接后自动加入下载列表」的初值，来自共用配置 */
  autoAdd: boolean
}>()

const emit = defineEmits<{
  close: []
  start: [payload: { urls: string[]; autoAdd: boolean }]
}>()

const text = ref('')
const autoAddChecked = ref(false)
const error = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      text.value = ''
      error.value = ''
      autoAddChecked.value = props.autoAdd
    }
  },
)

const urls = computed(() =>
  text.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean),
)

function submit() {
  if (!urls.value.length) {
    error.value = t('parse.batchParse.noLinks')

    return
  }

  // 与桌面版同一条判据：目前只支持 av / BV
  if (urls.value.some((url) => !url.includes('av') && !url.includes('BV'))) {
    error.value = t('parse.batchParse.invalid')

    return
  }

  emit('start', { urls: urls.value, autoAdd: autoAddChecked.value })
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('parse.batchParse.title')"
    width="600px"
    :close-on-mask="false"
    @close="emit('close')"
  >
    <div class="bar">
      <span class="count">{{ t('parse.batchParse.count', { count: urls.length }) }}</span>
      <span class="stretch" />
      <pushButton :title="t('parse.batchParse.clear')" @click="text = ''" />
    </div>

    <textarea
      v-model="text"
      class="lines"
      :placeholder="t('parse.batchParse.placeholder')"
      :aria-label="t('parse.batchParse.title')"
      @input="error = ''"
    ></textarea>

    <label class="auto-add">
      <transparentCheckBox v-model:checked="autoAddChecked" />
      <span>{{ t('parse.batchParse.autoAdd') }}</span>
    </label>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template #actions>
      <primaryPushButton :title="t('parse.batchParse.start')" @click="submit" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.count {
  font-size: 14px;
  color: var(--text-primary);
}

.stretch {
  flex: 1 1 auto;
}

.lines {
  font: inherit;
  font-size: 14px;
  box-sizing: border-box;
  width: 100%;
  min-height: 220px;
  resize: vertical;
  padding: 8px 10px;
  border-radius: 5px;
  outline: none;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  border-bottom-color: var(--control-stroke-input);
}

.lines:hover {
  background-color: var(--control-fill-secondary);
}

.lines:focus {
  background-color: var(--control-fill-input-active);
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 7px;
}

.lines::placeholder {
  color: var(--text-placeholder);
}

.auto-add {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
