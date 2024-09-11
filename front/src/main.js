import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { registerPlugins } from '@/plugins'
import VueApexCharts from "vue3-apexcharts"
import VueCountdown from '@chenfengyuan/vue-countdown'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const myCustomLightTheme = {
  dark: false,
  colors: {
    background: '#FFFFFF',
    surface: '#FFFFFF',
    primary: '#3B82F6',
    'primary-darken-1': '#1E3A8A',
    secondary: '#10B981',
    'secondary-darken-1': '#059669',
    error: '#EF4444',
    info: '#3B82F6',
    success: '#10B981',
    warning: '#F59E0B',
  },
  variables: {
    'border-color': '#E5E7EB',
    'border-radius-root': '8px',
    'font-weight-thin': 100,
    'font-weight-light': 300,
    'font-weight-regular': 400,
    'font-weight-medium': 500,
    'font-weight-bold': 700,
    'line-height-root': 1.5,
  },
}

const vuetify = createVuetify({
  theme: {
    defaultTheme: 'myCustomLightTheme',
    themes: {
      myCustomLightTheme,
    },
  },
  components,
  directives,
  defaults: {
    VCard: {
      elevation: 2,
      rounded: 'lg',
    },
    VBtn: {
      rounded: 'pill',
      fontWeight: 500,
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
    },
  },
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(vuetify)
app.use(VueApexCharts)
app.component(VueCountdown.name, VueCountdown)  // Register Vue-Countdown globally

registerPlugins(app)

app.mount('#app')