<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- Logo and Title -->
      <div class="auth-header">
        <img :src="logo" alt="Trading Platform" class="auth-logo" />
        <h1 class="auth-title">Trading Platform</h1>
        <p class="auth-subtitle">Experimental Market Research</p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="auth-loading">
        <div class="spinner"></div>
        <p>{{ loadingMessage }}</p>
      </div>

      <!-- Prolific Credential Form -->
      <div v-else-if="isProlificUser && !authStore.isAuthenticated" class="auth-form">
        <h2 class="form-title">Enter Your Credentials</h2>
        <p class="form-subtitle">Please enter your username and password to continue</p>

        <form @submit.prevent="handleProlificCredentialLogin">
          <div class="input-group">
            <label class="input-label">Username</label>
            <input
              v-model="username"
              type="text"
              class="input-field"
              placeholder="Enter username"
              :disabled="credentialLoading"
              required
            />
          </div>

          <div class="input-group">
            <label class="input-label">Password</label>
            <input
              v-model="password"
              type="password"
              class="input-field"
              placeholder="Enter password"
              :disabled="credentialLoading"
              required
            />
          </div>

          <button type="submit" class="btn btn-primary" :disabled="credentialLoading">
            {{ credentialLoading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>
      </div>

      <!-- Main Auth Options -->
      <div v-else class="auth-options">
        <p class="auth-message">
          {{ authStore.isAuthenticated ? 'Welcome back!' : 'Sign in to access the trading market' }}
        </p>

        <button 
          class="btn btn-google" 
          @click="signInWithGoogle"
          :disabled="googleLoading"
        >
          <svg class="google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          {{ authStore.isAuthenticated ? 'Continue to Trading' : 'Sign in with Google' }}
        </button>

        <div class="divider">
          <span>or</span>
        </div>

        <button 
          class="btn btn-secondary"
          @click="adminSignInWithGoogle"
          :disabled="adminLoading"
        >
          {{ authStore.isAuthenticated && authStore.isAdmin ? 'Go to Admin Dashboard' : 'Admin Access' }}
        </button>

        <button
          v-if="authStore.isAuthenticated"
          class="btn btn-text"
          @click="handleLogout"
        >
          Sign out
        </button>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="error-message">
        <span>{{ errorMessage }}</span>
        <button class="error-close" @click="errorMessage = ''">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'
import logo from '@/assets/trading_platform_logo.svg'

const props = defineProps({
  prolificPID: String,
  studyID: String,
  sessionID: String,
})

const route = useRoute()
const auth = getAuth()
const authStore = useAuthStore()
const sessionStore = useSessionStore()

// UI state
const errorMessage = ref('')
const isLoading = ref(false)
const loadingMessage = ref('Loading...')
const googleLoading = ref(false)
const adminLoading = ref(false)
const credentialLoading = ref(false)

// Prolific state
const isProlificUser = ref(false)
const username = ref('')
const password = ref('')
const prolificParams = ref(null)

const getProlificParams = () => {
  if (props.prolificPID && props.studyID && props.sessionID) {
    return {
      PROLIFIC_PID: props.prolificPID,
      STUDY_ID: props.studyID,
      SESSION_ID: props.sessionID,
    }
  }
  
  if (route.query.PROLIFIC_PID && route.query.STUDY_ID && route.query.SESSION_ID) {
    return {
      PROLIFIC_PID: route.query.PROLIFIC_PID,
      STUDY_ID: route.query.STUDY_ID,
      SESSION_ID: route.query.SESSION_ID,
    }
  }
  
  if (sessionStore.prolificParams) {
    return sessionStore.prolificParams
  }
  
  const stored = sessionStore.loadProlificParams()
  if (stored) {
    return stored
  }
  
  return null
}

onMounted(async () => {
  const params = getProlificParams()
  
  if (params) {
    isProlificUser.value = true
    prolificParams.value = params
    sessionStore.setProlificParams(params)
    
    const lastUsername = localStorage.getItem('prolific_last_username')
    const lastPassword = localStorage.getItem('prolific_last_password')
    if (lastUsername) username.value = lastUsername
    if (lastPassword) password.value = lastPassword
  }
  
  if (!isProlificUser.value && !authStore.isAuthenticated) {
    await authStore.initializeAuth()
  }
})

const handleLogout = async () => {
  await NavigationService.logout()
}

const signInWithGoogle = async () => {
  googleLoading.value = true
  errorMessage.value = ''
  
  try {
    if (authStore.isAuthenticated && authStore.traderId) {
      await NavigationService.afterLogin()
      return
    }
    
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    await authStore.login(result.user)
    await NavigationService.afterLogin()
  } catch (error) {
    console.error('Google sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during sign-in'
  } finally {
    googleLoading.value = false
  }
}

const adminSignInWithGoogle = async () => {
  adminLoading.value = true
  errorMessage.value = ''
  
  try {
    if (authStore.isAuthenticated && authStore.isAdmin) {
      await NavigationService.goToAdmin()
      return
    }
    
    if (authStore.isAuthenticated) {
      try {
        await authStore.adminLogin(auth.currentUser)
        if (authStore.isAdmin) {
          await NavigationService.goToAdmin()
          return
        } else {
          errorMessage.value = 'You do not have admin privileges.'
          return
        }
      } catch (e) {
        errorMessage.value = 'You do not have admin privileges.'
        return
      }
    }
    
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    await authStore.adminLogin(result.user)

    if (authStore.isAdmin) {
      await NavigationService.goToAdmin()
    } else {
      errorMessage.value = 'You do not have admin privileges.'
    }
  } catch (error) {
    console.error('Admin sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during admin sign-in'
  } finally {
    adminLoading.value = false
  }
}

const handleProlificCredentialLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = 'Please enter both username and password'
    return
  }

  credentialLoading.value = true
  errorMessage.value = ''

  try {
    await authStore.prolificLogin(prolificParams.value, {
      username: username.value,
      password: password.value,
    })

    localStorage.setItem('prolific_last_username', username.value)
    localStorage.setItem('prolific_last_password', password.value)

    await NavigationService.afterProlificLogin(prolificParams.value)
  } catch (error) {
    console.error('Prolific login error:', error)
    errorMessage.value = error.message || 'An error occurred during sign-in'
  } finally {
    credentialLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: var(--space-4);
}

.auth-container {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  box-shadow: var(--shadow-lg);
}

/* Header */
.auth-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.auth-logo {
  width: 80px;
  height: 80px;
  margin-bottom: var(--space-4);
}

.auth-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1) 0;
}

.auth-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
}

/* Loading */
.auth-loading {
  text-align: center;
  padding: var(--space-8) 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto var(--space-4);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-loading p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin: 0;
}

/* Form */
.auth-form {
  text-align: center;
}

.form-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
}

.form-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6) 0;
}

.input-group {
  margin-bottom: var(--space-4);
  text-align: left;
}

.input-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.input-field {
  width: 100%;
  padding: var(--space-3);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input-field:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.input-field::placeholder {
  color: var(--color-text-muted);
}

/* Options */
.auth-options {
  text-align: center;
}

.auth-message {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6) 0;
}

/* Buttons */
.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-google {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  border-color: var(--color-border);
  margin-bottom: var(--space-3);
}

.btn-google:hover:not(:disabled) {
  background: var(--color-bg-subtle);
  border-color: var(--color-text-muted);
}

.google-icon {
  flex-shrink: 0;
}

.btn-secondary {
  background: var(--color-bg-subtle);
  color: var(--color-text-secondary);
  border-color: var(--color-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.btn-text {
  background: transparent;
  color: var(--color-text-muted);
  border: none;
  font-size: var(--text-sm);
  margin-top: var(--space-4);
}

.btn-text:hover:not(:disabled) {
  color: var(--color-text-secondary);
}

/* Divider */
.divider {
  display: flex;
  align-items: center;
  margin: var(--space-4) 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.divider span {
  padding: 0 var(--space-3);
}

/* Error */
.error-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--color-error-light);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.error-close {
  background: none;
  border: none;
  color: var(--color-error);
  font-size: var(--text-lg);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

/* Responsive */
@media (max-width: 480px) {
  .auth-container {
    padding: var(--space-6);
  }
  
  .auth-logo {
    width: 64px;
    height: 64px;
  }
}
</style>
