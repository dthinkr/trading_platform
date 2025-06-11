import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { auth } from './firebaseConfig.js'
import './main.css'

// Create Vue app
const app = createApp(App)

// Enable Vue DevTools
app.config.devtools = true

// Create Pinia store
const pinia = createPinia()

// Use plugins
app.use(pinia)
app.use(router)

// Wait for Firebase Auth to initialize before mounting the app
let appMounted = false
auth.onAuthStateChanged(() => {
  if (!appMounted) {
    app.mount('#app')
    appMounted = true
  }
})