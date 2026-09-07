<script setup lang="ts">
// 下载哪些语言的字幕
//
// 配置是 `{ download_specified, specified_language }`：前者为假时下载全部可用字幕，
// 为真时只下勾选的那些。
//
// 语言表有 **158 条**，所以必须能搜。桌面版那个对话框是纯列表（窗口够大、可以滚），
// 网页上照搬会变成一段又长又难找的清单。

import { computed, ref, watch } from 'vue'
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'

export interface LanguageChoice {
  value: number | string
  label: string
}

const props = defineProps<{
  open: boolean
  choices: LanguageChoice[]
  value: { download_specified?: boolean; specified_language?: string[] } | null
}>()

const emit = defineEmits<{
  close: []
  save: [value: { download_specified: boolean; specified_language: string[] }]
}>()

const specified = ref(false)
const selected = ref<Set<string>>(new Set())
const keyword = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      specified.value = Boolean(props.value?.download_specified)
      selected.value = new Set(props.value?.specified_language ?? [])
      keyword.value = ''
    }
  },
)

const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()

  if (!text) {
    return props.choices
  }

  // 语言代码与中文名都能搜：记得住 "zh-Hant" 的和记得住「繁体」的都能找到
  return props.choices.filter(
    (choice) =>
      choice.label.toLowerCase().includes(text) ||
      String(choice.value).toLowerCase().includes(text),
  )
})

function toggle(value: string) {
  const next = new Set(selected.value)

  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }

  selected.value = next
}

function save() {
  emit('save', {
    download_specified: specified.value,
    // 顺序按语言表本身，不按用户勾选的先后 —— 存进配置的东西每次都该长得一样，
    // 否则 config.json 会因为「同一批语言的不同排列」反复产生无意义的差异
    specified_language: props.choices
      .map((choice) => String(choice.value))
      .filter((value) => selected.value.has(value)),
  })
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('settings.subtitleLanguage.title')"
    width="520px"
    @close="emit('close')"
  >
    <div class="modes">
      <label class="mode">
        <input type="radio" :checked="!specified" @change="specified = false" />
        <span>{{ t('settings.subtitleLanguage.all') }}</span>
      </label>
      <label class="mode">
        <input type="radio" :checked="specified" @change="specified = true" />
        <span>{{ t('settings.subtitleLanguage.specified') }}</span>
      </label>
    </div>

    <lineEdit
      v-model="keyword"
      type="search"
      :placeholder="t('settings.subtitleLanguage.search')"
      :disabled="!specified"
    />

    <ul class="list" :class="{ 'is-disabled': !specified }">
      <li v-for="choice in filtered" :key="String(choice.value)">
        <label>
          <input
            type="checkbox"
            :checked="selected.has(String(choice.value))"
            :disabled="!specified"
            @change="toggle(String(choice.value))"
          />
          <span class="label">{{ choice.label }}</span>
          <span class="code">{{ choice.value }}</span>
        </label>
      </li>

      <li v-if="!filtered.length" class="empty">{{ t('settings.subtitleLanguage.empty') }}</li>
    </ul>

    <template #actions>
      <span class="count">{{
        t('settings.subtitleLanguage.selected', { count: selected.size })
      }}</span>
      <primaryPushButton :title="t('settings.dialog.save')" @click="save" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.modes {
  display: flex;
  gap: 18px;
}

.mode {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-primary);
}

.list {
  flex: 1 1 auto;
  min-height: 220px;
  max-height: 42vh;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border-radius: 6px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

/* 只下指定语言没选中时整个列表灰掉，但**不隐藏** ——
   隐藏之后用户看不出这里还有个清单可以配 */
.list.is-disabled {
  opacity: 0.5;
}

.list label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.list.is-disabled label {
  cursor: default;
}

.list label:hover {
  background-color: var(--subtle-fill-secondary);
}

.label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}

.code {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--text-secondary);
}

.empty,
.count {
  font-size: 12px;
  color: var(--text-secondary);
}

.empty {
  padding: 10px 8px;
}

.count {
  margin-right: auto;
}
</style>
