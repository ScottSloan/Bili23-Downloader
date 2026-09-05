<script setup>
import { useThemeStore } from "@/stores/themeStore";

const themeStore = useThemeStore();

defineProps({
    placeholder: {
        type: String,
        default: ""
    },
    modelValue: {
        type: String,
        default: ""
    }
})

const emit = defineEmits(["update:modelValue", "submit"])
</script>

<template>
    <input
        class="fluent-line-edit"
        :class="themeStore.theme"
        :placeholder="placeholder"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
        @keyup.enter="emit('submit')"
    />
</template>

<style scoped>
.fluent-line-edit {
    border-radius: 5px;
    padding: 6px 10px;
    transition: background-color 0.2s ease, border-color 0.2s ease;
    font-size: 11pt;
    font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
    outline: none;
}

.fluent-line-edit.light {
    color: black;
    background-color: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(0, 0, 0, 0.05);
    border-bottom: 1px solid rgba(0, 0, 0, 0.39);
}

.fluent-line-edit.light::placeholder {
    color: rgb(141, 141, 142);
}

.fluent-line-edit.light:hover {
    background-color: rgba(249, 249, 249, 0.5);
    border: 1px solid rgba(0, 0, 0, 0.05);
    border-bottom: 1px solid rgba(0, 0, 0, 0.39);
}

.fluent-line-edit.light:focus {
    padding: 6px 10px 5px 10px;
    border-bottom: 2px solid var(--primary-color);
    background-color: white;
}

.fluent-line-edit.dark {
    color: white;
    background-color: rgba(255, 255, 255, 0.0605);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: 1px solid rgba(255, 255, 255, 0.5442);
}

.fluent-line-edit.dark::placeholder {
    color: rgb(154, 154, 154);
    user-select: none;
}

.fluent-line-edit.dark:hover {
    background-color: rgba(255, 255, 255, 0.0837);
}

.fluent-line-edit.dark:focus {
    padding: 6px 10px 5px 10px;
    background: rgba(30, 30, 30, 0.7);
    border-bottom: 2px solid var(--primary-color);
}

</style>
