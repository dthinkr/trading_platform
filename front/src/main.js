import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { registerPlugins } from '@/plugins'
import VueApexCharts from "vue3-apexcharts"
import VueCountdown from '@chenfengyuan/vue-countdown'
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { auth } from "./firebaseConfig.js";

// Create Vue app
const app = createApp(App)

app.use(router) // Use the router
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)

registerPlugins(app)

auth.onAuthStateChanged(() => {
  app.mount('#app')
})