import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import './styles/global.css'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import App from './App.vue'
import router from './router'

NProgress.configure({ showSpinner: false, speed: 400, minimum: 0.2 })

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
