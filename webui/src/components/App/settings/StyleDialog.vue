<script setup lang="ts">
// 弹幕 / 字幕样式
//
// 两者共用这一个对话框：字段大半相同（字体、边框、分辨率），弹幕多一组「高级」
// （轨道排布相关），字幕多颜色、边距、对齐。
//
// **只在 ASS 格式下生效** —— 其余格式（xml / srt / json…）没有样式一说。
// 卡片上的说明写明了这一点，与桌面版同一句措辞。
//
// 字体名的下拉来自 `/api/settings/fonts`，**列的是服务端装了哪些字体**（ASS 在服务端
// 生成，弹幕轨道还要靠 QFontMetrics 量宽度）。枚举不到时退回自由输入框 ——
// 实测 Windows 上 offscreen 一款都枚举不到，那不是错误，是常态。

import { computed, ref, watch } from 'vue'
import { t } from '@/i18n'
import { assToRgba, rgbaToAss } from './assColor'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import spinBox from '@/components/Fluent/components/widgets/spin_box/SpinBox.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import switchButton from '@/components/Fluent/components/widgets/switch_button/SwitchButton.vue'

type Kind = 'danmaku' | 'subtitle'

interface NumberField {
  /** 在配置字典里的路径，如 ['font', 'size'] */
  path: string[]
  min: number
  max: number
  decimals?: number
}

const props = defineProps<{
  open: boolean
  kind: Kind
  value: Record<string, unknown> | null
  /** 服务端的字体列表。空数组表示枚举不到，改用自由输入 */
  fonts: string[]
  alignments: { value: string | number; label: string }[]
}>()

const emit = defineEmits<{
  close: []
  save: [value: Record<string, unknown>]
}>()

// 编辑中的副本。深拷贝：直接改 store 里那份的话，点「取消」也已经改掉了
const draft = ref<Record<string, never>>({} as Record<string, never>)

watch(
  () => props.open,
  (open) => {
    if (open) {
      draft.value = JSON.parse(JSON.stringify(props.value ?? {}))
    }
  },
)

/** 各字段的取值范围，与桌面版 gui/component/setting/group.py 里的 setRange 一一对应 */
const NUMBER_FIELDS: NumberField[] = [
  { path: ['font', 'size'], min: 1, max: 1000 },
  { path: ['border', 'border'], min: 0, max: 100, decimals: 1 },
  { path: ['border', 'shadow'], min: 0, max: 100, decimals: 1 },

  { path: ['advanced', 'display_area'], min: 10, max: 100 },
  { path: ['advanced', 'opacity'], min: 10, max: 100 },
  { path: ['advanced', 'scroll_duration'], min: 3, max: 15 },
  { path: ['advanced', 'static_duration'], min: 3, max: 15 },
  { path: ['advanced', 'minimum_gap'], min: 0, max: 300 },

  { path: ['margin', 'left'], min: -1000, max: 1000 },
  { path: ['margin', 'right'], min: -1000, max: 1000 },
  { path: ['margin', 'vertical'], min: -1000, max: 1000 },

  { path: ['resolution', 'width'], min: 1, max: 10000 },
  { path: ['resolution', 'height'], min: 1, max: 10000 },
]

const FONT_FLAGS = ['bold', 'italic', 'underline', 'strike'] as const
const COLOR_KEYS = ['primary', 'secondary', 'border', 'shadow'] as const

/**
 * 取一个字段的 min / max / decimals，直接 v-bind 给 SpinBox
 *
 * **只返回 SpinBox 认得的那几个键**：把整个 NumberField 摊上去的话，`path`（一个数组）
 * 会作为未声明的 attr 落到根元素上，变成 `path="font,size"` 这样的脏属性
 */
function fieldOf(path: string[]): { min: number; max: number; decimals: number } {
  const field = NUMBER_FIELDS.find((entry) => entry.path.join('.') === path.join('.'))

  return {
    min: field?.min ?? Number.NEGATIVE_INFINITY,
    max: field?.max ?? Number.POSITIVE_INFINITY,
    decimals: field?.decimals ?? 0,
  }
}

function read(path: string[]): unknown {
  return path.reduce<unknown>(
    (node, key) => (node == null ? undefined : (node as Record<string, unknown>)[key]),
    draft.value,
  )
}

function write(path: string[], value: unknown) {
  let node = draft.value as unknown as Record<string, unknown>

  for (const key of path.slice(0, -1)) {
    if (typeof node[key] !== 'object' || node[key] === null) {
      node[key] = {}
    }

    node = node[key] as Record<string, unknown>
  }

  node[path[path.length - 1]] = value
}

function num(path: string[]): number {
  return Number(read(path)) || 0
}

function label(key: string): string {
  return t(`settings.style.${key}`)
}

/** 颜色：配置里存的是 ASS 串，界面上拆成取色器 + 不透明度 */
function colorOf(key: string) {
  return assToRgba(read(['color', key]))
}

function setColorHex(key: string, hex: string) {
  write(['color', key], rgbaToAss(hex, colorOf(key).alpha))
}

function setColorAlpha(key: string, alpha: number) {
  write(['color', key], rgbaToAss(colorOf(key).hex, alpha))
}

const fontOptions = computed(() => {
  const families = props.fonts

  if (!families.length) {
    return []
  }

  const current = String(read(['font', 'name']) ?? '')

  // 当前配置的字体不在服务端列表里时也要能选中，否则一打开对话框，
  // 下拉框会自动落到第一项，用户什么都没做就换掉了字体
  const all = families.includes(current) && current ? families : [current, ...families]

  return all.filter(Boolean).map((family) => ({ value: family, label: family }))
})
</script>

<template>
  <fluentDialog
    :open="open"
    :title="
      kind === 'danmaku' ? t('settings.style.danmakuTitle') : t('settings.style.subtitleTitle')
    "
    width="520px"
    @close="emit('close')"
  >
    <template #hint>{{ t('settings.style.hint') }}</template>

    <div class="scroller">
      <!-- ---- 字体 ---- -->
      <section>
        <h3>{{ t('settings.style.sectionFont') }}</h3>

        <div class="grid">
          <label>
            <span>{{ label('fontName') }}</span>
            <comboBox
              v-if="fontOptions.length"
              :model-value="String(read(['font', 'name']) ?? '')"
              :options="fontOptions"
              :label="label('fontName')"
              @update:model-value="(value) => write(['font', 'name'], value)"
            />
            <!-- 服务端枚举不到字体时只能自由输入。这时名字对不对由用户负责 -->
            <lineEdit
              v-else
              :model-value="String(read(['font', 'name']) ?? '')"
              :placeholder="t('settings.style.fontNamePlaceholder')"
              @update:model-value="(value) => write(['font', 'name'], value)"
            />
          </label>

          <label>
            <span>{{ label('fontSize') }}</span>
            <spinBox
              :model-value="num(['font', 'size'])"
              v-bind="fieldOf(['font', 'size'])"
              :label="label('fontSize')"
              @update:model-value="(value) => write(['font', 'size'], value)"
            />
          </label>
        </div>

        <div class="flags">
          <label v-for="flag in FONT_FLAGS" :key="flag" class="flag">
            <switchButton
              :model-value="Boolean(read(['font', flag]))"
              :label="label(flag)"
              @update:model-value="(value) => write(['font', flag], value)"
            />
            <span>{{ label(flag) }}</span>
          </label>
        </div>
      </section>

      <!-- ---- 边框 ---- -->
      <section>
        <h3>{{ t('settings.style.sectionBorder') }}</h3>

        <div class="grid">
          <label v-for="key in ['border', 'shadow']" :key="key">
            <span>{{ label(key === 'border' ? 'outline' : 'shadow') }}</span>
            <spinBox
              :model-value="num(['border', key])"
              v-bind="fieldOf(['border', key])"
              :label="label(key === 'border' ? 'outline' : 'shadow')"
              @update:model-value="(value) => write(['border', key], value)"
            />
          </label>
        </div>
      </section>

      <!-- ---- 弹幕专有 ---- -->
      <section v-if="kind === 'danmaku'">
        <h3>{{ t('settings.style.sectionAdvanced') }}</h3>

        <div class="grid">
          <label
            v-for="key in [
              'display_area',
              'opacity',
              'scroll_duration',
              'static_duration',
              'minimum_gap',
            ]"
            :key="key"
          >
            <span>{{ label(key) }}</span>
            <spinBox
              :model-value="num(['advanced', key])"
              v-bind="fieldOf(['advanced', key])"
              :label="label(key)"
              @update:model-value="(value) => write(['advanced', key], value)"
            />
          </label>
        </div>
      </section>

      <!-- ---- 字幕专有 ---- -->
      <template v-if="kind === 'subtitle'">
        <section>
          <h3>{{ t('settings.style.sectionColor') }}</h3>

          <div class="grid">
            <label v-for="key in COLOR_KEYS" :key="key" class="color-field">
              <span>{{ label(`color_${key}`) }}</span>
              <div class="color-row">
                <input
                  type="color"
                  :value="colorOf(key).hex"
                  :aria-label="label(`color_${key}`)"
                  @input="setColorHex(key, ($event.target as HTMLInputElement).value)"
                />
                <spinBox
                  :model-value="colorOf(key).alpha"
                  :min="0"
                  :max="255"
                  :label="`${label(`color_${key}`)} ${t('settings.style.alpha')}`"
                  :suffix="t('settings.style.alpha')"
                  @update:model-value="(value) => setColorAlpha(key, value)"
                />
              </div>
            </label>
          </div>
        </section>

        <section>
          <h3>{{ t('settings.style.sectionMargin') }}</h3>

          <div class="grid">
            <label v-for="key in ['left', 'right', 'vertical']" :key="key">
              <span>{{ label(`margin_${key}`) }}</span>
              <spinBox
                :model-value="num(['margin', key])"
                v-bind="fieldOf(['margin', key])"
                :label="label(`margin_${key}`)"
                @update:model-value="(value) => write(['margin', key], value)"
              />
            </label>
          </div>
        </section>

        <section>
          <h3>{{ label('alignment') }}</h3>

          <comboBox
            :model-value="Number(read(['alignment']) ?? 2)"
            :options="alignments"
            :label="label('alignment')"
            @update:model-value="(value) => write(['alignment'], Number(value))"
          />
        </section>
      </template>

      <!-- ---- 分辨率 ---- -->
      <section>
        <h3>{{ t('settings.style.sectionResolution') }}</h3>

        <div class="grid">
          <label v-for="key in ['width', 'height']" :key="key">
            <span>{{ label(`screen_${key}`) }}</span>
            <spinBox
              :model-value="num(['resolution', key])"
              v-bind="fieldOf(['resolution', key])"
              :label="label(`screen_${key}`)"
              @update:model-value="(value) => write(['resolution', key], value)"
            />
          </label>
        </div>
      </section>
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.save')" @click="emit('save', draft)" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.scroller {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-right: 4px;
}

section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

h3 {
  margin: 0;
  font-size: 11pt;
  font-weight: 600;
  color: var(--text-primary);
}

/* 两列，与桌面版那几个 QGridLayout 的排法一致 */
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}

.grid label,
.color-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.grid label > span {
  font-size: 10pt;
  color: var(--text-secondary);
}

.flags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
}

.flag {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-primary);
}

.color-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-row input[type='color'] {
  width: 42px;
  height: 30px;
  flex: 0 0 auto;
  padding: 2px;
  border-radius: 5px;
  cursor: pointer;
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
}
</style>
