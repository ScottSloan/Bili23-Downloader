<script setup>
import transparentCheckBox from '@/components/Fluent/components/widgets/checkbox/TransparentCheckBox.vue';
import { useThemeStore } from '@/stores/themeStore';

const themeStore = useThemeStore();

const emit = defineEmits(['update:checked']);

defineProps({
    title: {
        type: String,
        default: "Title"
    },
    cover: {
        type: String,
        default: ""
    },
    desc: {
        type: String,
        default: ""
    },
    uploader: {
        type: String,
        default: ""
    },
    checked: {
        type: Boolean,
        default: false
    }
})
</script>

<template>
    <div class="parse-list-card rounded" :class="themeStore.theme">
        <transparentCheckBox :checked="checked" @update:checked="emit('update:checked', $event)" />
        <img :src="cover" class="rounded" alt="Cover" v-if="cover" draggable="false"/>
        <span class="card-title">{{ title }}</span>

        <div class="info-row" v-if="desc">
            <span class="card-desc">{{ uploader }}</span>
            <span class="card-desc">{{ desc }}</span>
        </div>
    </div>
</template>

<style scoped>
.parse-list-card {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 230px;
    user-select: none;
    padding: 10px;
}
.parse-list-card img {
    width: 230px;
    height: 130px;
}
.parse-list-card .card-title {
    font-size: 11pt;
    margin-top: 8px;
}
.parse-list-card .card-desc {
    font-size: 10pt;
    margin-top: 4px;
}
.parse-list-card .info-row {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    gap: 10px;
}

.parse-list-card.light:hover {
    background-color: rgba(0, 0, 0, 0.05);
}

.parse-list-card.light .card-desc {
    color: rgb(130, 130, 130);
}

.parse-list-card.dark:hover {
    background-color: rgba(255, 255, 255, 0.05);
}

.parse-list-card.dark .card-desc {
    color: rgb(150, 150, 150);
}
</style>