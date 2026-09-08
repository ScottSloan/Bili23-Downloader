<script setup lang="ts">
/**
 * 三态复选框
 *
 * 对应解析列表里那个 —— 桌面版由 `TreeItemDelegate._drawCheckBox` 手画，
 * 度量照抄：19×19、圆角 4.5，未选时是淡填充 + 一圈描边，选中与半选时整块填主题色，
 * 里面的勾 / 横杠用 `--text-on-accent`（浅色主题下是白的，深色下是黑的，
 * 与 qfluentwidgets 的 `getIconColor(reverse=True)` 一致）。
 *
 * **与 `TransparentCheckBox` 不是一个东西**：那个是浮在封面图上的毛玻璃款，
 * 有背景模糊与高光；这个是列表里的常规款。
 *
 * 底下是一个真的 `<input type="checkbox">`，外观全靠兄弟元素画 ——
 * Tab 可达、空格切换、读屏软件认得的状态都由它提供。半选态额外补
 * `aria-checked="mixed"`，原生 `indeterminate` 只影响外观不进无障碍树。
 */
import { computed } from 'vue'
import { FLUENT_ICONS } from '../../../icons/fluentIcons'

const props = withDefaults(
  defineProps<{
    /** 0 未选 / 1 半选 / 2 选中。与 core 的 CheckState 同序 */
    state?: number
    disabled?: boolean
    label?: string
  }>(),
  {
    state: 0,
    disabled: false,
    label: '',
  },
)

const emit = defineEmits<{
  (event: 'change', checked: boolean): void
}>()

const glyph = computed(() => (props.state === 2 ? FLUENT_ICONS.checkAccept : FLUENT_ICONS.checkPartial))

function onChange(event: Event) {
  emit('change', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <span class="fluent-check-box" :class="{ 'is-disabled': disabled }">
    <input
      type="checkbox"
      :checked="state === 2"
      :indeterminate="state === 1"
      :aria-checked="state === 1 ? 'mixed' : state === 2"
      :disabled="disabled"
      :aria-label="label || undefined"
      @change="onChange"
      @click.stop
    />

    <span class="box" :class="{ 'is-on': state !== 0 }">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <svg v-if="state !== 0" :viewBox="glyph.viewBox" aria-hidden="true" v-html="glyph.body" />
    </span>
  </span>
</template>

<style scoped>
.fluent-check-box {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  width: 19px;
  height: 19px;
}

/* 输入框只保留功能，视觉全交给 .box —— 但不能 display:none，
   那会让它从无障碍树和 Tab 序里一起消失 */
.fluent-check-box input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.fluent-check-box.is-disabled input {
  cursor: default;
}

.box {
  box-sizing: border-box;
  width: 19px;
  height: 19px;
  border-radius: 4.5px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background-color 0.1s ease,
    border-color 0.1s ease;

  background-color: var(--check-box-fill);
  border: 1px solid var(--check-box-stroke);
}

.box.is-on {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  /* 勾 / 横杠的颜色：浅色主题白、深色主题黑，与主题色底刚好互补 */
  color: var(--text-on-accent);
}

.box svg {
  width: 19px;
  height: 19px;
}

.fluent-check-box:hover .box:not(.is-on) {
  border-color: var(--text-secondary);
}

.fluent-check-box input:focus-visible + .box {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 2px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

.fluent-check-box.is-disabled .box {
  opacity: 0.4;
}

/* 取值来自 TreeItemDelegate._drawCheckBox */
.fluent-check-box {
  --check-box-fill: rgba(0, 0, 0, 0.024);
  --check-box-stroke: rgba(0, 0, 0, 0.478);
}

:root[data-theme='dark'] .fluent-check-box {
  --check-box-fill: rgba(0, 0, 0, 0.102);
  --check-box-stroke: rgba(255, 255, 255, 0.557);
}
</style>
