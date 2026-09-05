// Fluent 图标组件集中导出
//
// 图标一律内联成 Vue 组件，不再以路径字符串引用 src/assets 下的 svg 文件。两个原因：
//
// 1. 字符串字面量（icon="/src/assets/icon/search.svg"）不会被 Vite 当成资源引用，
//    既不打包也不改写路径。dev 下能显示只是因为 dev server 直接按路径伺服源码目录，
//    生产构建的 dist 里根本没有这些 svg，必然 404。
// 2. 内联之后可以用 fill="currentColor" 跟随文字颜色，深浅主题共用一份文件，
//    不必像 GUI 那样在 src/res/icon/{light,dark}/ 下备两套。
//
// 新增图标：把 svg 内容抄进一个新的 IconXxx.vue，根节点写 fill="currentColor"
// （描边类图标则写 stroke="currentColor"），再在此处补一行导出。
export { default as IconApp } from './IconApp.vue'
export { default as IconDownload } from './IconDownload.vue'
export { default as IconSearch } from './IconSearch.vue'
export { default as IconSettings } from './IconSettings.vue'
