<script setup>
import { useThemeStore } from "@/stores/themeStore";

const themeStore = useThemeStore();

defineProps({
    title: {
        type: String,
        required: true
    },
    variant: {
        type: String,
        default: "push"
    }
})
</script>

<template>
    <div class="fluent-button" :class="[themeStore.theme, `is-${variant}`]">
        <span>{{ title }}</span>
    </div>
</template>

<style scoped>
.fluent-button {
    text-align: center;
    display: inline-block;
    flex: 0 0 auto;
    justify-content: space-between;
    padding: 5px 12px 6px 12px;
    border-radius: 5px;
    cursor: pointer;
    user-select: none;
    transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.fluent-button.light {
    background-color: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(0, 0, 0, 0.073);
    border-bottom: 1px solid rgba(0, 0, 0, 0.183);
    color: black;
}

.fluent-button.light:hover {
    background-color: rgba(249, 249, 249, 0.5);
}

.fluent-button.light:active {
    color: rgba(0, 0, 0, 0.63);
    background-color: rgba(249, 249, 249, 0.3);
    border-bottom: 1px solid rgba(0, 0, 0, 0.073);
}

.fluent-button.dark {
    background-color: rgba(255, 255, 255, 0.0605);
    border: 1px solid rgba(255, 255, 255, 0.053);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    color: white;
}

.fluent-button.dark:hover {
    background-color: rgba(255, 255, 255, 0.0837);
}

.fluent-button.dark:active {
    color: rgba(255, 255, 255, 0.786);
    background-color: rgba(255, 255, 255, 0.0326);
    border-top: 1px solid rgba(255, 255, 255, 0.053);
}
</style>