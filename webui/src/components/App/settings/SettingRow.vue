<script setup lang="ts">
// 把清单里的一项渲染成一张卡片
//
// **控件类型、取值范围、默认值、是否需要重启，全部来自后端下发的 schema**，
// 不在前端重复声明（理由见 spec.ts 开头）。这里只负责：按类型挑控件、
// 按 enabledWhen 决定灰不灰、把改动交给 store。

import { computed, ref } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { t } from '@/i18n'
import { SPEC_BY_ATTR, type SettingSpec } from './spec'
import settingCard from '@/components/Fluent/components/settings/SettingCard.vue'
import settingGroupRow from '@/components/Fluent/components/settings/SettingGroupRow.vue'
import switchButton from '@/components/Fluent/components/widgets/switch_button/SwitchButton.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import spinBox from '@/components/Fluent/components/widgets/spin_box/SpinBox.vue'
import fluentSlider from '@/components/Fluent/components/widgets/slider/FluentSlider.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import directoryPickerDialog from './DirectoryPickerDialog.vue'

const props = defineProps<{
  spec: SettingSpec
  /** 结构化项在卡片右侧显示的一句摘要（当前首选画质、已选几种语言…），由设置页算好传进来 */
  summary?: string
  /**
   * 这一行是在折叠卡片里，还是自己独占一张卡片
   *
   * 两者的外壳不同（`GroupWidget` vs `SettingCard`：缩进、高度、有没有边框），
   * 但里面挑控件、判依赖、存值那一整套完全一样，所以只换外壳，不复制一份组件
   */
  inGroup?: boolean
}>()

const emit = defineEmits<{
  /** 值变了。语言那种改完要立刻反映到界面上的项，由父组件接住 */
  changed: [attr: string, value: unknown]
  /** 结构化项要开专用的对话框。对话框统一由设置页托管，不散落在每一行里 */
  openDialog: [attr: string]
}>()

const store = useSettingsStore()

const shell = computed(() => (props.inGroup ? settingGroupRow : settingCard))

const pickerOpen = ref(false)

const item = computed(() => store.item(props.spec.attr))

/** 后端下发的类型 → 用哪个控件。spec 里显式指定的优先 */
const kind = computed(() => {
  if (props.spec.kind) {
    return props.spec.kind
  }

  switch (item.value?.type) {
    case 'bool':
      return 'switch'
    case 'enum':
      return 'combo'
    case 'int':
    case 'float':
      return 'spin'
    default:
      return 'text'
  }
})

const enabled = computed(() => isEnabled(props.spec.attr))

/**
 * 依赖是否满足。**要沿着链一路往上看**
 *
 * 「嵌入后删除字幕文件」依赖「嵌入字幕」，后者又依赖「下载字幕」。只判一层的话，
 * 关掉「下载字幕」之后「嵌入字幕」是灰了，但它的值仍然是 true —— 孙子项照样亮着，
 * 用户能去改一个根本不会生效的开关。
 *
 * depth 只是防环：清单是手写的，写出一个自我依赖不至于让页面直接卡死
 */
function isEnabled(attr: string, depth = 0): boolean {
  const condition = SPEC_BY_ATTR[attr]?.enabledWhen

  if (!condition || depth > 8) {
    return true
  }

  const other = store.value(condition.attr)
  const satisfied = condition.equals === undefined ? Boolean(other) : other === condition.equals

  return satisfied && isEnabled(condition.attr, depth + 1)
}

const label = computed(() => translate(`settings.label.${props.spec.attr}`, props.spec.attr))

const description = computed(() =>
  props.spec.described ? translate(`settings.desc.${props.spec.attr}`, '') : '',
)

/**
 * action 那一行按钮上的字
 *
 * 「自定义…」是给结构化项用的（那些确实是在自定义一张表），放在「登录口令」旁边
 * 不知所云。所以按 attr 单配一条，没配的回落到「自定义…」
 */
const actionLabel = computed(() =>
  translate(`settings.actionLabel.${props.spec.attr}`, t('settings.customize')),
)

/** t() 取不到时会原样返回 key，这里换成给定的兜底值 */
function translate(key: string, fallback: string): string {
  const text = t(key)

  return text === key ? fallback : text
}

const options = computed(() => {
  const raw = item.value?.options

  if (!Array.isArray(raw)) {
    return []
  }

  return raw.map((value) => ({
    value: value as string | number,
    label: optionLabel(value as string | number),
  }))
})

/**
 * 选项名
 *
 * 文件格式（ass / mp4 / nfo…）不进 i18n：三种语言下都是同一个大写缩写，
 * 列出来只是徒增几十条要维护的串。取不到译文就直接大写显示
 */
function optionLabel(value: string | number): string {
  const key = `settings.option.${props.spec.attr}.${value}`
  const text = t(key)

  if (text !== key) {
    return text
  }

  return typeof value === 'string' ? value.toUpperCase() : String(value)
}

const range = computed(() => {
  const raw = item.value?.range

  return Array.isArray(raw) && raw.length === 2
    ? { min: Number(raw[0]), max: Number(raw[1]) }
    : { min: Number.NEGATIVE_INFINITY, max: Number.POSITIVE_INFINITY }
})

// 类型断言写在这里而不是模板里：模板中的 `as string | number` 会被 Vue 编译器
// 当成 Vue 2 的过滤器语法（那个 `|`），eslint 直接报 vue/no-deprecated-filter
const comboValue = computed(() => item.value?.value as string | number)

/** 改完要不要重启后端。清单里显式写了就听它的，没写才用后端下发的标记 */
const needsRestart = computed(() => props.spec.restart ?? Boolean(item.value?.restart))

function update(value: unknown) {
  store.set(props.spec.attr, value as never, needsRestart.value)

  emit('changed', props.spec.attr, value)
}
</script>

<template>
  <!--
    后端没有这一项就整张卡片不出现。后端可能是旧版本，界面上少一项好过报错。

    `action` 是例外：它本来就没有对应的配置项（见 spec.ts 里 ControlKind 的说明）。
    因为这个 v-if 不再能把 item 收窄成非空，下面一律用 `item?.`
  -->
  <component
    :is="shell"
    v-if="item || kind === 'action'"
    :title="label"
    :icon="spec.icon ?? ''"
    :description="description"
    :disabled="!enabled"
    :restart="needsRestart"
    :restart-hint="t('settings.restartBadge')"
  >
    <switchButton
      v-if="kind === 'switch'"
      :model-value="Boolean(item?.value)"
      :disabled="!enabled"
      :label="label"
      :on-text="t('settings.switch.on')"
      :off-text="t('settings.switch.off')"
      @update:model-value="update"
    />

    <comboBox
      v-else-if="kind === 'combo'"
      :model-value="comboValue"
      :options="options"
      :disabled="!enabled"
      :label="label"
      @update:model-value="update"
    />

    <spinBox
      v-else-if="kind === 'spin'"
      :model-value="Number(item?.value)"
      :min="range.min"
      :max="range.max"
      :step="spec.step ?? 1"
      :decimals="spec.decimals ?? (item?.type === 'float' ? 1 : 0)"
      :suffix="spec.suffix ?? ''"
      :disabled="!enabled"
      :label="label"
      @update:model-value="update"
    />

    <fluentSlider
      v-else-if="kind === 'slider'"
      :model-value="Number(item?.value)"
      :min="range.min"
      :max="range.max"
      :step="spec.step ?? 1"
      :disabled="!enabled"
      :label="label"
      @update:model-value="update"
    />

    <!--
      后端没有对应配置项的一行，只有一个按钮，收尾归对话框自己。
      放在 dialog 之前：两者都要开对话框，但这一支不读 store 里的值
    -->
    <pushButton
      v-else-if="kind === 'action'"
      :title="actionLabel"
      @click="emit('openDialog', spec.attr)"
    />

    <template v-else-if="kind === 'dialog'">
      <span v-if="summary" class="summary">{{ summary }}</span>
      <pushButton
        :title="t('settings.customize')"
        :disabled="!enabled"
        @click="emit('openDialog', spec.attr)"
      />
    </template>

    <template v-else-if="kind === 'path'">
      <span class="path-value" :title="String(item?.value)">{{ item?.value || '—' }}</span>
      <pushButton :title="t('settings.picker.title')" @click="pickerOpen = true" />

      <directoryPickerDialog
        :open="pickerOpen"
        :current="String(item?.value ?? '')"
        @close="pickerOpen = false"
        @select="
          (chosen) => {
            update(chosen)
            pickerOpen = false
          }
        "
      />
    </template>

    <lineEdit
      v-else
      class="text-value"
      :model-value="String(item?.value ?? '')"
      :type="kind === 'password' ? 'password' : 'text'"
      :disabled="!enabled"
      :aria-label="label"
      @update:model-value="update"
    />
  </component>
</template>

<style scoped>
.path-value {
  max-width: 320px;
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-value {
  width: 260px;
}

.summary {
  max-width: 260px;
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
