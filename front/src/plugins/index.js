/**
 * plugins/index.js
 *
 * Automatically included in `./src/main.js`
 */

// Plugins
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import routes from '@/router'  // Import routes, not the router instance
import { auth } from '@/firebaseConfig'

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

const pinia = createPinia()

// Create the router here with the correct base
const router = createRouter({
  history: createWebHistory('/trading/'),  // Set the base path here
  routes
})

router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const currentUser = auth.currentUser

  if (requiresAuth && !currentUser) {
    next('/trading/register')
  } else if (to.path === '/trading/register' && currentUser) {
    next('/trading/CreateTradingSession')
  } else {
    next()
  }
})

export function registerPlugins (app) {
  app
    .use(vuetify)
    .use(router)
    .use(pinia)
}

export { router }
