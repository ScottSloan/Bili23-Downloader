<script setup lang="ts">
/**
 * 复选框
 *
 * 对齐 qfluentwidgets 的 `CheckBox`（`check_box.py` 的 `paintEvent` + `check_box.qss`）：
 *
 * | | 值 | 出处 |
 * |---|---|---|
 * | 方框 | 18×18，圆角 4.5 | qss 的 `indicator` + `drawRoundedRect(rect, 4.5, 4.5)` |
 * | 方框到文字 | 8 | qss 的 `spacing` |
 * | 文字 | 14px | `setFont(self)` 的默认值 |
 * | 未选：描边 / 填充 | `rgba(0,0,0,122)` / `rgba(0,0,0,6)` | `_borderColor` / `_backgroundColor` |
 * | 悬停 | 描边 143、填充 13 | 同上 |
 * | 选中 / 半选 | 整块填主题色，勾与横杠用反色 | `getIconColor(reverse=True)` |
 *
 * **解析列表里那个是 19×19**，不是 18 —— 那一个由 `tree_view.py` 的委托手画，
 * 库里这两处本来就差 1px。所以给了 `size`，树形列表显式传 19。
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
    /**
     * 无障碍名称
     *
     * 带 `text` 时不必给：文字本身就是名字。只有方框、名字在别处（列表行）时才要
     */
    label?: string
    /** 显示在方框右边的文字。给了它整个控件就是一个可点的 label */
    text?: string
    /** 方框边长。默认 18，解析列表传 19 */
    size?: number
  }>(),
  {
    state: 0,
    disabled: false,
    label: '',
    text: '',
    size: 18,
  },
)

const emit = defineEmits<{
  (event: 'change', checked: boolean): void
}>()

const glyph = computed(() => (props.state === 2 ? FLUENT_ICONS.checkAccept : FLUENT_ICONS.checkPartial))

const boxStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))

function onChange(event: Event) {
  emit('change', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <!--
    有文字时用 <label> 包住：点文字也能切换，这是原生行为，自己监听 click 反而
    要处理选中文本、拖拽等一堆边角
  -->
  <component
    :is="text ? 'label' : 'span'"
    class="fluent-check-box"
    :class="{ 'is-disabled': disabled, 'has-text': !!text }"
  >
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

    <span class="box" :class="{ 'is-on': state !== 0 }" :style="boxStyle">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <svg v-if="state !== 0" :viewBox="glyph.viewBox" aria-hidden="true" v-html="glyph.body" />
    </span>

    <span v-if="text" class="text">{{ text }}</span>
  </component>
</template>

<style scoped>
.fluent-check-box {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
}

.fluent-check-box.has-text {
  /* qss 的 spacing: 8px */
  gap: 8px;
  cursor: pointer;
  /* qss 的 min-height: 22px，好让相邻两行的间距与桌面版一致 */
  min-height: 22px;
}

.fluent-check-box.has-text.is-disabled {
  cursor: default;
}

/* 输入框只保留功能，视觉全交给 .box —— 但不能 display:none，
   那会让它从无障碍树和 Tab 序里一起消失 */
.fluent-check-box input {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: inherit;
}

/* 只有方框时（列表行里）输入框就压在方框上，此时它自己要是手型 */
.fluent-check-box:not(.has-text) input {
  cursor: pointer;
}

.fluent-check-box.is-disabled input {
  cursor: default;
}

.box {
  box-sizing: border-box;
  flex: 0 0 auto;
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
  width: 100%;
  height: 100%;
}

.text {
  font-size: 14px;
  line-height: 20px;
  color: var(--text-primary);
  user-select: none;
}

.fluent-check-box.is-disabled .text {
  color: var(--text-disabled);
}

/* 悬停：未选时描边加深、底色加重（_borderColor / _backgroundColor 的 HOVER 一档） */
.fluent-check-box:hover .box:not(.is-on) {
  --check-box-fill: rgba(0, 0, 0, 0.051);
  --check-box-stroke: rgba(0, 0, 0, 0.561);
}

:root[data-theme='dark'] .fluent-check-box:hover .box:not(.is-on) {
  --check-box-fill: rgba(255, 255, 255, 0.043);
  --check-box-stroke: rgba(255, 255, 255, 0.553);
}

.fluent-check-box:hover .box.is-on {
  background-color: var(--primary-color-light-1);
  border-color: var(--primary-color-light-1);
}

:root[data-theme='dark'] .fluent-check-box:hover .box.is-on {
  background-color: var(--primary-color-dark-1);
  border-color: var(--primary-color-dark-1);
}

.fluent-check-box input:focus-visible + .box {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 2px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

.fluent-check-box.is-disabled .box {
  opacity: 0.4;
}

/* 取值来自 check_box.py 的 _borderColor / _backgroundColor（NORMAL 一档），
   与 tree_view.py 委托里画的那个是同一组数 */
.fluent-check-box {
  --check-box-fill: rgba(0, 0, 0, 0.024);
  --check-box-stroke: rgba(0, 0, 0, 0.478);
}

:root[data-theme='dark'] .fluent-check-box {
  --check-box-fill: rgba(0, 0, 0, 0.102);
  --check-box-stroke: rgba(255, 255, 255, 0.557);
}
</style>
