<script setup lang="ts">
/** 样式变体：push 为普通按钮，primary 为主色按钮 */
type ButtonVariant = 'push' | 'primary'

withDefaults(
  defineProps<{
    /** 按钮文字。声明成 prop，因此不会落到 <button> 的 title 属性上变成气泡提示 */
    title: string
    variant?: ButtonVariant
    /** 禁用态。用原生 disabled，浏览器不会给禁用控件派发 click，无需再手动拦截 */
    disabled?: boolean
    /**
     * 原生 button 的 type
     *
     * 默认 button 而不是浏览器默认的 submit —— 表单外的按钮占绝大多数，
     * 让它们意外提交表单是更常见的错。表单里的提交按钮显式传 'submit'
     */
    type?: 'button' | 'submit' | 'reset'
  }>(),
  {
    variant: 'push',
    disabled: false,
    type: 'button',
  },
)
</script>

<template>
  <!--
    必须是原生 <button>：div 在无障碍树里根本不暴露，Tab 也走不到。
    换成 button 之后 Tab 可达、Enter/Space 触发、disabled 语义全部由浏览器提供。
    根元素只有一个，@click / class / style 仍按 attrs fallthrough 落在这里。
  -->
  <button :type="type" class="fluent-button" :class="`is-${variant}`" :disabled="disabled">
    <span>{{ title }}</span>
  </button>
</template>

<style scoped>
.fluent-button {
  text-align: center;
  display: inline-block;
  flex: 0 0 auto;
  padding: 5px 12px 6px 12px;
  border-radius: 5px;
  cursor: pointer;
  user-select: none;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease;

  /* 抹掉浏览器给 <button> 的默认样式：字体不继承、自带外边距、原生外观。
     font 简写连 line-height 一并继承，文本高度才能和原先的 <div> 一致 */
  font: inherit;
  margin: 0;
  appearance: none;
  /* <button> 的 UA 默认值是 border-box，原先的 <div> 是 content-box。
     显式写死，免得调用方给的宽高含义随元素类型变 */
  box-sizing: border-box;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  /* Fluent 的立体感来自与其余三边不同的那一条：浅色在底边，深色在顶边 */
  border-bottom-color: var(--control-stroke-accent);
}

:root[data-theme='dark'] .fluent-button {
  border-bottom-color: var(--control-stroke-default);
  border-top-color: var(--control-stroke-accent);
}

/* 悬停 / 按下都要排除禁用态：各浏览器对禁用控件是否匹配 :hover 的行为并不一致 */
.fluent-button:not(:disabled):hover {
  background-color: var(--control-fill-secondary);
}

.fluent-button:not(:disabled):active {
  color: var(--text-pressed);
  background-color: var(--control-fill-tertiary);
  border-bottom-color: var(--control-stroke-default);
}

:root[data-theme='dark'] .fluent-button:not(:disabled):active {
  border-top-color: var(--control-stroke-default);
}

/* ---- 键盘焦点 ---- */
/*
  Fluent 的焦点环是双环：贴着控件的 1px 浅色内环 + 包在外面的 2px 深色外环。
  内环用 box-shadow 撑出 1px，外环用 outline + outline-offset: 1px 正好接上，
  这样在 Windows 高对比度模式下 outline 仍会被系统强制画出来。
  只在 :focus-visible 生效，鼠标点击不出现焦点环。
*/
.fluent-button:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

/* ---- 禁用 ---- */
/*
  var() 的第二个值是 tokens.css 补齐前的兜底，等新 token 落地后可以删掉。
  禁用时四条边同色 —— Fluent 会去掉那条制造立体感的深色边
*/
.fluent-button:disabled {
  cursor: default;
  color: var(--text-disabled);
  background-color: var(--control-fill-tertiary);
  border-color: var(--control-stroke-default);
}

/* 深色下基础规则用 :root[data-theme] 提了权重，禁用态要跟上才盖得住 border-top-color */
:root[data-theme='dark'] .fluent-button:disabled {
  border-color: var(--control-stroke-default);
}

/* ---- primary ---- */
.fluent-button.is-primary {
  color: var(--text-on-accent);
  background-color: var(--primary-color);
  border-color: var(--primary-color-light-1);
  border-bottom-color: var(--primary-color-dark-1);
}

:root[data-theme='dark'] .fluent-button.is-primary {
  border-bottom-color: var(--primary-color-light-2);
  border-top-color: var(--primary-color-light-1);
}

.fluent-button.is-primary:not(:disabled):hover {
  background-color: var(--primary-color-light-1);
  border-color: var(--primary-color-light-2);
  border-bottom-color: var(--primary-color-dark-1);
}

:root[data-theme='dark'] .fluent-button.is-primary:not(:disabled):hover {
  background-color: var(--primary-color-dark-1);
  border-color: var(--primary-color-light-1);
  border-bottom-color: var(--primary-color-light-2);
}

.fluent-button.is-primary:not(:disabled):active {
  color: color-mix(in srgb, var(--text-on-accent) 63%, transparent);
  background-color: var(--primary-color-light-3);
  border-color: var(--primary-color-light-3);
}

:root[data-theme='dark'] .fluent-button.is-primary:not(:disabled):active {
  background-color: var(--primary-color-dark-2);
  border-color: var(--primary-color-dark-2);
}

/* 主色按钮禁用后不再带主题色，退成中性灰，与 Fluent 一致 */
.fluent-button.is-primary:disabled {
  color: var(--text-on-accent-disabled);
  background-color: var(--accent-fill-disabled);
  border-color: var(--accent-fill-disabled);
}

:root[data-theme='dark'] .fluent-button.is-primary:disabled {
  border-color: var(--accent-fill-disabled);
}
</style>
