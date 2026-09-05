<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/themeStore'

const themeStore = useThemeStore()
const route = useRoute()

const props = defineProps({
  title: {
    type: String,
    default: '',
  },

  icon: {
    type: String,
    default: '',
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
    <a
      class="navigation-bar-button"
      :class="{ active: isActive, [themeStore.theme]: true }"
      :href="href"
      @click="navigate"
    >
      <svg v-if="icon" :src="icon" alt="Button Icon">
        <use :href="icon" width="20" height="20" />
      </svg>

      <span>{{ title }}</span>
    </a>
  </RouterLink>

  <div v-else class="navigation-bar-button" :class="{ active: isActive, [themeStore.theme]: true }">
    <svg v-if="icon" :src="icon" alt="Button Icon">
      <use :href="icon" width="20" height="20" />
    </svg>

    <span>{{ title }}</span>
  </div>
</template>

<style scoped>
.navigation-bar-button {
  position: relative;
  appearance: none;
  text-decoration: none;
  color: inherit;
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

.navigation-bar-button.active {
  color: var(--primary-color);
}

.navigation-bar-button.light.active {
  background-color: white;
}

.navigation-bar-button.light:not(.active) {
  color: rgba(0, 0, 0, 0.6);
}

.navigation-bar-button.light:hover:not(.active) {
  color: black;
  background-color: rgba(0, 0, 0, 0.035);
}

.navigation-bar-button.dark.active {
  background-color: rgba(255, 255, 255, 0.164);
}

.navigation-bar-button.dark:not(.active) {
  color: rgba(255, 255, 255, 0.6);
}

.navigation-bar-button.dark:hover:not(.active) {
  color: white;
  background-color: rgba(255, 255, 255, 0.035);
}
</style>
