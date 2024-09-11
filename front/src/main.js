import { createApp } from 'vue'
import App from './App.vue'
import { registerPlugins } from '@/plugins'
import VueApexCharts from "vue3-apexcharts"
import VueCountdown from '@chenfengyuan/vue-countdown'

// Remove these imports as they're now handled in plugins/index.js
// import { createPinia } from 'pinia'
// import 'vuetify/styles'
// import { createVuetify } from 'vuetify'
// import * as components from 'vuetify/components'
// import * as directives from 'vuetify/directives'

const app = createApp(App)

// Remove this line as Pinia is now initialized in plugins/index.js
// const pinia = createPinia()

// Remove these lines as they're now handled in registerPlugins
// app.use(pinia)
// app.use(vuetify)

app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)  // Register Vue-Countdown globally

registerPlugins(app)

app.mount('#app')