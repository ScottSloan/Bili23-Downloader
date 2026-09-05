<script setup lang="ts">
import { computed } from 'vue'
import type { Component, PropType } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const props = defineProps({
  title: {
    type: String,
    default: '',
  },

  // 图标传的是组件本身（见 @/components/Fluent/icons），不是 svg 路径字符串。
  // 函数式组件也是合法取值，故运行期类型写成 [Object, Function]
  icon: {
    type: [Object, Function] as PropType<Component | null>,
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
})

const isActive = computed(() => props.active || (props.to ? route.path === props.to : false))
</script>

<template>
  <RouterLink v-if="to" :to="to" custom v-slot="{ navigate, href }">
    <a class="navigation-bar-button" :class="{ active: isActive }" :href="href" @click="navigate">
      <component :is="icon" v-if="icon" />

      <span>{{ title }}</span>
    </a>
  </RouterLink>

  <div v-else class="navigation-bar-button" :class="{ active: isActive }">
    <component :is="icon" v-if="icon" />

    <span>{{ title }}</span>
  </div>
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
}

.navigation-bar-button svg {
  width: 20px;
  height: 20px;
  margin-top: 6px;
}

.navigation-bar-button span {
  font-size: 9pt;
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
</style>
