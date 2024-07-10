import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import { registerPlugins } from '@/plugins'
import App from './App.vue'
import VueCountdown from '@chenfengyuan/vue-countdown'

// Import Vuetify styles
import 'vuetify/styles'
import 'animate.css'

const myCustomLightTheme = {
  dark: false,
  colors: {
    background: '#F3F4F6',
    surface: '#FFFFFF',
    primary: '#1E40AF',
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

app.component(VueCountdown.name, VueCountdown)
registerPlugins(app)

app.use(vuetify)
app.mount('#app')