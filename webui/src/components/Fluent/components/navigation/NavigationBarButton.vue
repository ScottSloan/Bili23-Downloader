<script setup lang="ts">
import { computed } from 'vue'
import type { Component, PropType } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import fluentIcon from '../../icons/FluentIcon.vue'

const route = useRoute()

const props = defineProps({
  title: {
    type: String,
    default: '',
  },

  /**
   * 图标。两种传法：
   *
   * - **组件本身**（见 @/components/Fluent/icons）—— 手抄进 IconXxx.vue 的那几个。
   *   函数式组件也合法，故运行期类型写成 [Object, Function]
   * - **名字字符串** —— 从 Qt 资源抽出来、集中放在 fluentIcons.ts 里的那批。
   *   那些路径数据动辄几 KB，再手抄一份进 IconXxx.vue 不值当
   */
  icon: {
    type: [Object, Function, String] as PropType<Component | string | null>,
    default: null,
  },

  active: {
    type: Boolean,
    default: false,
  },

  to: {
    type: String,
    default: '',
  },

  /**
   * 角标上的数字。0 或负数不显示
   *
   * 与桌面版一致：超过 99 显示 "99+"（见 main_window.py 的
   * update_download_btn_badge_info）—— 三位数在 64px 宽的按钮上摆不下
   */
  badge: {
    type: Number,
    default: 0,
  },
})

const badgeText = computed(() => (props.badge > 99 ? '99+' : String(props.badge)))

const isActive = computed(() => props.active || (props.to ? route.path === props.to : false))
</script>

<template>
  <RouterLink v-if="to" :to="to" custom v-slot="{ navigate, href }">
    <a class="navigation-bar-button" :class="{ active: isActive }" :href="href" @click="navigate">
      <fluentIcon v-if="typeof icon === 'string'" :name="icon" />
      <component :is="icon" v-else-if="icon" />

      <span>{{ title }}</span>
      <span v-if="badge > 0" class="badge">{{ badgeText }}</span>
    </a>
  </RouterLink>

  <!--
    不指向某一页的那种（桌面版里「关于」就是 `selectable = False` 加一个 onClick）。
    用 <button> 而不是 <div>：Tab 走得到、回车与空格能触发，读屏软件也知道它可以点
  -->
  <button v-else type="button" class="navigation-bar-button" :class="{ active: isActive }">
    <fluentIcon v-if="typeof icon === 'string'" :name="icon" />
    <component :is="icon" v-else-if="icon" />

    <span>{{ title }}</span>
    <span v-if="badge > 0" class="badge">{{ badgeText }}</span>
  </button>
</template>

<style scoped>
.navigation-bar-button {
  position: relative;
  appearance: none;
  text-decoration: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  width: 64px;
  height: 58px;
  border-radius: 5px;
  margin-bottom: 5px;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;

  color: var(--text-secondary);
  /* 抹掉 <button> 那一支自带的浏览器默认值，让两支长得一模一样 */
  font: inherit;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
}

.navigation-bar-button:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: -2px;
}

.navigation-bar-button svg {
  width: 20px;
  height: 20px;
  margin-top: 6px;
}

.navigation-bar-button span {
  /* NavigationBarPushButton 的 setFont(self, 11) */
  font-size: 11px;
  text-align: center;
  user-select: none;
}

.navigation-bar-button:hover:not(.active) {
  color: var(--text-primary);
  background-color: var(--subtle-fill-secondary);
}

.navigation-bar-button.active {
  color: var(--primary-color);
  background-color: var(--subtle-fill-selected);
}

/* 角标压在图标右上角。绝对定位是为了不占布局空间 ——
   否则数字一出现，图标与文字会整体往上跳一下 */
.badge {
  position: absolute;
  top: 4px;
  right: 6px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  box-sizing: border-box;
  border-radius: 8px;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  user-select: none;

  color: var(--text-on-accent);
  background-color: var(--text-danger);
}
</style>
