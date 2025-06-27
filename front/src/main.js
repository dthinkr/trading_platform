import { createApp } from 'vue'
import App from './App.vue'
import { registerPlugins } from '@/plugins'
import VueApexCharts from 'vue3-apexcharts'
import VueCountdown from '@chenfengyuan/vue-countdown'
import { auth } from './firebaseConfig.js'
import './global.css'
import '@mdi/font/css/materialdesignicons.css'
import { Toaster } from 'vue-sonner'

// Create Vue app
const app = createApp(App)

// Explicitly enable Vue DevTools
app.config.devtools = true

// Use additional plugins not handled by registerPlugins
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)
app.component('Toaster', Toaster)

// Register all main plugins (Vuetify, Pinia, Router, Motion)
registerPlugins(app)

// Wait for Firebase Auth to initialize before mounting the app
let appMounted = false
auth.onAuthStateChanged(() => {
  if (!appMounted) {
    app.mount('#app')
    appMounted = true
  }
})
