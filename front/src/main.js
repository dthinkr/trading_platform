import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerPlugins } from '@/plugins'
import VueApexCharts from "vue3-apexcharts"
import VueCountdown from '@chenfengyuan/vue-countdown'
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { auth } from "./firebaseConfig.js";

// Create Pinia store
const pinia = createPinia()

// Create Vue app
const app = createApp(App)

app.use(pinia) // Use Pinia for state management
app.use(router) // Use the router
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)

registerPlugins(app)

// Wait for Firebase Auth to initialize before mounting the app
let appMounted = false
auth.onAuthStateChanged(() => {
  if (!appMounted) {
    app.mount('#app')
    appMounted = true
  }
})