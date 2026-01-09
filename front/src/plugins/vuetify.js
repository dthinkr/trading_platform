/**
 * plugins/vuetify.js
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Composables
import { createVuetify } from 'vuetify'

/**
 * Trading Platform Design System - Vuetify Theme
 * Colors aligned with design-tokens.css
 */
export default createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          // Primary - Main brand color
          primary: '#4F46E5',
          'primary-darken-1': '#4338CA',
          
          // Secondary - Neutral gray
          secondary: '#4B5563',
          
          // Semantic colors
          error: '#EF4444',
          info: '#3B82F6',
          success: '#10B981',
          warning: '#F59E0B',
          
          // Surface colors
          background: '#F9FAFB',
          surface: '#FFFFFF',
          'surface-variant': '#F3F4F6',
          
          // Text colors
          'on-background': '#111827',
          'on-surface': '#111827',
          'on-primary': '#FFFFFF',
        }
      }
    }
  },
  defaults: {
    VBtn: {
      variant: 'flat',
      rounded: 'md',
    },
    VCard: {
      rounded: 'lg',
      elevation: 0,
    },
    VTextField: {
      variant: 'outlined',
      density: 'compact',
    },
    VSelect: {
      variant: 'outlined',
      density: 'compact',
    },
    VTextarea: {
      variant: 'outlined',
      density: 'compact',
    },
  }
})
