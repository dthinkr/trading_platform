import axios from 'axios'
import { auth } from '@/firebaseConfig'
import router from '@/router' // You'll need to export router from your router file

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
})

// Helper to show global error notifications
const showGlobalError = async (message) => {
  try {
    const { useUIStore } = await import('@/store/ui')
    const uiStore = useUIStore()
    uiStore.showError(message)
  } catch (e) {
    console.error('Could not show error notification:', e)
  }
}

instance.interceptors.request.use(
  async (config) => {
    try {
      // Import the auth store to check for Prolific token
      const { useAuthStore } = await import('@/store/auth')
      const authStore = useAuthStore()

      // Check for Prolific token first
      if (authStore.prolificToken) {
        // Using Prolific token for authentication
        config.headers.Authorization = `Prolific ${authStore.prolificToken}`
      }
      // Fall back to Firebase authentication if no Prolific token
      else if (auth.currentUser) {
        // Force token refresh if it's close to expiring
        const user = auth.currentUser
        const tokenResult = await user.getIdTokenResult()
        const expirationTime = new Date(tokenResult.expirationTime).getTime()
        const now = Date.now()

        // If token expires in less than 5 minutes, refresh it
        if (expirationTime - now < 5 * 60 * 1000) {
          const newToken = await user.getIdToken(true)
          config.headers.Authorization = `Bearer ${newToken}`
        } else {
          config.headers.Authorization = `Bearer ${tokenResult.token}`
        }
      }
      return config
    } catch (error) {
      console.error('Error refreshing token:', error)
      return Promise.reject(error)
    }
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.data?.message || ''
      
      if (status === 401) {
        // Check if user is logged in
        if (auth.currentUser) {
          try {
            // Try to refresh token
            const token = await auth.currentUser.getIdToken(true)
            error.config.headers.Authorization = `Bearer ${token}`
            return axios(error.config)
          } catch (refreshError) {
            // If refresh fails, force logout
            await auth.signOut()
            router.push('/')
            return Promise.reject(error)
          }
        } else {
          // No user logged in, redirect to login
          router.push('/')
          return Promise.reject(error)
        }
      }
      
      if (status === 403 && detail.includes('Maximum number of markets reached')) {
        error.message = 'You have reached the maximum number of allowed markets.'
        showGlobalError(error.message)
      } else if (status >= 500) {
        // Server errors - show generic message
        error.message = detail || 'Server error occurred. Please try again later.'
        showGlobalError(error.message)
      } else if (status >= 400 && status !== 401) {
        // Client errors (except auth) - show the detail if available
        error.message = detail || 'An error occurred'
        // Show error for non-validation errors (4xx except 400 validation)
        if (status !== 400 || !detail.includes('validation')) {
          showGlobalError(error.message)
        }
      } else {
        error.message = detail || 'An error occurred'
      }
    } else if (error.request) {
      error.message = 'No response received from server'
      showGlobalError('Unable to connect to server. Please check your connection.')
    } else {
      error.message = 'Error setting up the request'
    }
    return Promise.reject(error)
  }
)

export default instance
