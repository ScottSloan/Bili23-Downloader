<script setup lang="ts">
// 命名规则
//
// 配置是一张表：每条 `{ id, name, type, rule, default }`。`type` 是媒体类型
// （单个视频 / 多 P / 合集 / 番剧 …），每种类型有且只有一条**默认规则**，
// 下载时按条目的类型挑那一条。
//
// 校验与预览都走后端（`/api/settings/naming-rule/preview`）：判据在
// `util/format/naming_rule.py`，桌面版的编辑对话框用的是同一份。
// 前端自己判的话，迟早出现「桌面版存得下的规则 WebUI 说非法」。

import { computed, ref, watch } from 'vue'
import { settings as settingsApi, ApiError } from '@/api'
import type { NamingRulePreviewResult } from '@/api'
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import switchButton from '@/components/Fluent/components/widgets/switch_button/SwitchButton.vue'

export interface NamingRule {
  id: string
  name: string
  type: number
  rule: string
  default?: boolean
}

interface Variable {
  variable: string
  description: string
  example: string
}

const props = defineProps<{
  open: boolean
  value: NamingRule[]
}>()

const emit = defineEmits<{
  close: []
  save: [value: NamingRule[]]
}>()

const rules = ref<NamingRule[]>([])
const types = ref<{ value: number; label: string }[]>([])

/** 正在编辑的那条。null 表示在看列表 */
const editing = ref<NamingRule | null>(null)
const variables = ref<Variable[]>([])
// 用生成的类型而不是手写一份：后端那几个字段是 Optional，生成出来是
// `string | null | undefined`，手写成 `string | undefined` 会对不上
const preview = ref<NamingRulePreviewResult | null>(null)
const error = ref('')

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      return
    }

    rules.value = JSON.parse(JSON.stringify(props.value ?? []))
    editing.value = null
    error.value = ''

    if (!types.value.length) {
      try {
        types.value = (await settingsApi.namingRuleTypes()).types.map((entry) => ({
          value: Number(entry.value),
          label: entry.label,
        }))
      } catch (e) {
        error.value = e instanceof ApiError ? e.message : String(e)
      }
    }
  },
)

const typeLabel = computed(() => new Map(types.value.map((entry) => [entry.value, entry.label])))

/**
 * 预置规则的名字在配置里存的是键（`DEFAULT_FOR_NORMAL`），显示时要翻成人话
 *
 * 桌面版是把翻译后的名字**写回配置**的（`rule_list.py` 的 init_rule_list）。
 * 这里不跟着写回：那样一改语言，名字就停在旧语言上。只在显示时翻，存的仍是键
 */
function displayName(rule: NamingRule): string {
  const key = `settings.namingRule.preset.${rule.name}`
  const text = t(key)

  return text === key ? rule.name : text
}

function startEdit(rule: NamingRule) {
  editing.value = JSON.parse(JSON.stringify(rule))

  void loadVariables()
}

function startAdd() {
  editing.value = {
    // crypto.randomUUID 在 https 与 localhost 下都可用；退化时用时间戳拼一个，
    // id 只需要在这张表里唯一
    id:
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `rule-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    name: '',
    type: types.value[0]?.value ?? 11,
    rule: '',
    default: false,
  }

  void loadVariables()
}

function remove(index: number) {
  // 与桌面版一致：默认规则不能删。删掉的话该类型就没有规则可用了
  if (rules.value[index]?.default) {
    error.value = t('settings.namingRule.cannotDeleteDefault')

    return
  }

  rules.value = rules.value.filter((_, position) => position !== index)
}

async function loadVariables() {
  if (!editing.value) {
    return
  }

  preview.value = null

  try {
    variables.value = (await settingsApi.namingRuleVariables(editing.value.type)).variables
  } catch {
    variables.value = []
  }
}

async function runPreview() {
  if (!editing.value) {
    return
  }

  try {
    preview.value = await settingsApi.namingRulePreview(editing.value.type, editing.value.rule)
  } catch (e) {
    preview.value = { valid: false, message: e instanceof ApiError ? e.message : String(e) }
  }
}

function insertVariable(variable: string) {
  if (editing.value) {
    editing.value.rule += variable
  }
}

/** 保存正在编辑的那条，回到列表 */
async function commitEdit() {
  const entry = editing.value

  if (!entry) {
    return
  }

  if (!entry.name.trim()) {
    error.value = t('settings.namingRule.nameRequired')

    return
  }

  // 存进去之前必须过一遍校验：这里放行的话，下载时才发现规则非法，
  // 那时报错离用户设它的地方已经很远了
  const result = await settingsApi
    .namingRulePreview(entry.type, entry.rule)
    .catch(() => ({ valid: false, message: t('settings.namingRule.previewFailed') }))

  preview.value = result

  if (!result.valid) {
    error.value = result.message || t('settings.namingRule.invalid')

    return
  }

  error.value = ''

  const index = rules.value.findIndex((item) => item.id === entry.id)

  if (index >= 0) {
    rules.value[index] = entry
  } else {
    rules.value.push(entry)
  }

  // 一种类型只能有一条默认规则 —— 设了新的就把同类型的其他都取消，
  // 与桌面版 _set_default_rule 一致
  if (entry.default) {
    for (const item of rules.value) {
      if (item.type === entry.type) {
        item.default = item.id === entry.id
      }
    }
  }

  editing.value = null
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="editing ? t('settings.namingRule.editTitle') : t('settings.namingRule.title')"
    width="640px"
    @close="emit('close')"
  >
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <!-- ---- 列表 ---- -->
    <template v-if="!editing">
      <div class="toolbar">
        <pushButton :title="t('settings.namingRule.add')" @click="startAdd" />
      </div>

      <ul class="list">
        <li v-for="(rule, index) in rules" :key="rule.id">
          <div class="info">
            <div class="name">
              {{ displayName(rule) }}
              <span v-if="rule.default" class="tag">{{ t('settings.namingRule.default') }}</span>
            </div>
            <div class="meta">
              {{ typeLabel.get(rule.type) ?? rule.type }} · <code>{{ rule.rule }}</code>
            </div>
          </div>

          <pushButton :title="t('settings.namingRule.edit')" @click="startEdit(rule)" />
          <pushButton
            :title="t('settings.namingRule.delete')"
            :disabled="rule.default"
            @click="remove(index)"
          />
        </li>
      </ul>
    </template>

    <!-- ---- 编辑单条 ---- -->
    <template v-else>
      <div class="fields">
        <label>
          <span>{{ t('settings.namingRule.name') }}</span>
          <lineEdit v-model="editing.name" />
        </label>

        <label>
          <span>{{ t('settings.namingRule.type') }}</span>
          <comboBox
            :model-value="editing.type"
            :options="types"
            :label="t('settings.namingRule.type')"
            @update:model-value="
              (value) => {
                editing!.type = Number(value)
                loadVariables()
              }
            "
          />
        </label>
      </div>

      <label class="rule-field">
        <span>{{ t('settings.namingRule.rule') }}</span>
        <lineEdit v-model="editing.rule" @submit="runPreview" />
      </label>

      <div class="rule-actions">
        <switchButton v-model="editing.default" :label="t('settings.namingRule.setDefault')" />
        <span class="default-label">{{ t('settings.namingRule.setDefault') }}</span>
        <span class="spacer"></span>
        <pushButton :title="t('settings.namingRule.preview')" @click="runPreview" />
      </div>

      <p v-if="preview" class="preview" :class="{ invalid: !preview.valid }">
        <template v-if="preview.valid">
          {{
            t('settings.namingRule.previewResult', {
              folder: preview.folder || '—',
              filename: preview.filename || '',
            })
          }}
        </template>
        <template v-else>{{ preview.message }}</template>
      </p>

      <!-- 变量表：点一下就追加到规则末尾，省得手抄 -->
      <ul class="variables">
        <li v-for="entry in variables" :key="entry.variable">
          <button type="button" @click="insertVariable(entry.variable)">
            <code>{{ entry.variable }}</code>
            <span class="desc">{{ entry.description }}</span>
            <span class="example">{{ entry.example }}</span>
          </button>
        </li>
      </ul>
    </template>

    <template #actions>
      <template v-if="editing">
        <pushButton :title="t('settings.dialog.cancel')" @click="editing = null" />
        <primaryPushButton :title="t('settings.namingRule.done')" @click="commitEdit" />
      </template>
      <template v-else>
        <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
        <primaryPushButton :title="t('settings.dialog.save')" @click="emit('save', rules)" />
      </template>
    </template>
  </fluentDialog>
</template>

<style scoped>
.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}

.toolbar {
  display: flex;
  gap: 8px;
}

.list,
.variables {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 46vh;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border-radius: 6px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
}

.list li:hover {
  background-color: var(--subtle-fill-secondary);
}

.info {
  flex: 1 1 auto;
  min-width: 0;
}

.name {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.meta {
  margin-top: 2px;
  font-size: 9.5pt;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag {
  font-size: 8.5pt;
  padding: 1px 6px;
  border-radius: 10px;
  color: var(--text-on-accent);
  background-color: var(--primary-color);
}

.fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}

.fields label,
.rule-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.fields label > span,
.rule-field > span {
  font-size: 10pt;
  color: var(--text-secondary);
}

.rule-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.default-label {
  font-size: 10pt;
  color: var(--text-primary);
}

.spacer {
  flex: 1 1 auto;
}

.preview {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 10pt;
  color: var(--text-primary);
  background-color: var(--control-fill-secondary);
  word-break: break-all;
}

.preview.invalid {
  color: var(--text-danger);
}

.variables button {
  appearance: none;
  font: inherit;
  width: 100%;
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 5px 8px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.variables button:hover {
  background-color: var(--subtle-fill-secondary);
}

.variables code {
  flex: 0 0 auto;
  min-width: 150px;
  font-family: Consolas, 'Courier New', monospace;
  color: var(--primary-color);
}

.desc {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 10pt;
}

.example {
  flex: 0 0 auto;
  font-size: 9.5pt;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

code {
  font-family: Consolas, 'Courier New', monospace;
}
</style>
