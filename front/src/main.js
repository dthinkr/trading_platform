import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerPlugins } from '@/plugins'
import VueApexCharts from "vue3-apexcharts"
import VueCountdown from '@chenfengyuan/vue-countdown'
import { auth } from "./firebaseConfig.js"
import './global.css'
import '@mdi/font/css/materialdesignicons.css'
// Create Vue app
const app = createApp(App)

// Explicitly enable Vue DevTools
app.config.devtools = true

// Create Pinia store
const pinia = createPinia()

// Use plugins
app.use(pinia) // Use Pinia for state management
app.use(router) // Use the router
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)

// Register other plugins (only once)
registerPlugins(app)

// Wait for Firebase Auth to initialize before mounting the app
let appMounted = false
auth.onAuthStateChanged(() => {
  if (!appMounted) {
    app.mount('#app')
    appMounted = true
  }
})