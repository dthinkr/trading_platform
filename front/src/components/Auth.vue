<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4" />
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>

            <!-- Loading indicator for authentication -->
            <div v-if="isLoading" class="text-center my-6">
              <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
              <p class="text-subtitle-1 mt-4">{{ loadingMessage }}</p>
            </div>

            <!-- Prolific user credential form -->
            <div
              v-else-if="isProlificUser && !authStore.isAuthenticated"
              class="text-center my-6"
            >
              <h2 class="text-h5 font-weight-bold mb-4">Enter Your Credentials</h2>
              <p class="text-subtitle-2 mb-4">
                Please enter your username and password to continue
              </p>

              <v-form @submit.prevent="handleProlificCredentialLogin" class="mb-4">
                <v-text-field
                  v-model="username"
                  label="Username"
                  required
                  variant="outlined"
                  class="mb-3"
                  :disabled="credentialLoading"
                ></v-text-field>

                <v-text-field
                  v-model="password"
                  label="Password"
                  type="password"
                  required
                  variant="outlined"
                  class="mb-4"
                  :disabled="credentialLoading"
                ></v-text-field>

                <v-btn
                  type="submit"
                  block
                  color="primary"
                  size="x-large"
                  :loading="credentialLoading"
                >
                  Login
                </v-btn>
              </v-form>
            </div>

            <!-- Regular authentication UI -->
            <template v-else-if="!authStore.isAuthenticated">
              <p class="text-subtitle-1 mb-6">Sign in to access a trading market</p>

              <v-btn 
                block 
                color="error" 
                size="x-large" 
                @click="signInWithGoogle" 
                class="mb-4"
                :loading="googleLoading"
              >
                <v-icon start icon="mdi-google"></v-icon>
                Sign in with Google
              </v-btn>

              <v-btn
                block
                color="primary"
                size="x-large"
                @click="adminSignInWithGoogle"
                class="mb-4"
                :loading="adminLoading"
              >
                <v-icon start icon="mdi-google"></v-icon>
                Admin Sign in with Google
              </v-btn>
            </template>

            <!-- Already authenticated - show redirect message -->
            <template v-else>
              <p class="text-subtitle-1 mb-6">You are already signed in. Redirecting...</p>
              <v-progress-circular indeterminate color="primary" size="32"></v-progress-circular>
            </template>

            <v-alert
              v-if="errorMessage"
              type="error"
              class="mt-4"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'
import logo from '@/assets/trading_platform_logo.svg'

// Props from router
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

// Check for Prolific params from multiple sources
const getProlificParams = () => {
  // 1. From props (URL query params via router)
  if (props.prolificPID && props.studyID && props.sessionID) {
    return {
      PROLIFIC_PID: props.prolificPID,
      STUDY_ID: props.studyID,
      SESSION_ID: props.sessionID,
    }
  }
  
  // 2. From route query directly
  if (route.query.PROLIFIC_PID && route.query.STUDY_ID && route.query.SESSION_ID) {
    return {
      PROLIFIC_PID: route.query.PROLIFIC_PID,
      STUDY_ID: route.query.STUDY_ID,
      SESSION_ID: route.query.SESSION_ID,
    }
  }
  
  // 3. From session store (persisted)
  if (sessionStore.prolificParams) {
    return sessionStore.prolificParams
  }
  
  // 4. From localStorage (legacy support)
  const stored = sessionStore.loadProlificParams()
  if (stored) {
    return stored
  }
  
  return null
}

onMounted(async () => {
  // Check for Prolific parameters
  const params = getProlificParams()
  
  if (params) {
    isProlificUser.value = true
    prolificParams.value = params
    sessionStore.setProlificParams(params)
    
    // Auto-fill credentials if stored
    const lastUsername = localStorage.getItem('prolific_last_username')
    const lastPassword = localStorage.getItem('prolific_last_password')
    if (lastUsername) username.value = lastUsername
    if (lastPassword) password.value = lastPassword
  }
  
  // If already authenticated, redirect to appropriate page
  if (authStore.isAuthenticated) {
    isLoading.value = true
    loadingMessage.value = 'Redirecting...'
    
    try {
      await NavigationService.afterLogin()
    } catch (error) {
      console.error('Redirect failed:', error)
      isLoading.value = false
    }
  } else if (!isProlificUser.value) {
    // Initialize Firebase auth listener for regular users
    await authStore.initializeAuth()
    
    // Check again after init
    if (authStore.isAuthenticated && authStore.traderId) {
      await NavigationService.afterLogin()
    }
  }
})

// Google sign-in for regular users
const signInWithGoogle = async () => {
  googleLoading.value = true
  errorMessage.value = ''
  
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    const user = result.user

    await authStore.login(user)
    await NavigationService.afterLogin()
  } catch (error) {
    console.error('Google sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during sign-in'
  } finally {
    googleLoading.value = false
  }
}

// Admin sign-in
const adminSignInWithGoogle = async () => {
  adminLoading.value = true
  errorMessage.value = ''
  
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    const user = result.user

    await authStore.adminLogin(user)

    if (authStore.isAdmin) {
      await NavigationService.goToAdmin()
    } else {
      errorMessage.value = 'You do not have admin privileges.'
    }
  } catch (error) {
    console.error('Admin Google sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during admin sign-in'
  } finally {
    adminLoading.value = false
  }
}

// Prolific credential login
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

    // Store credentials for future auto-fill
    localStorage.setItem('prolific_last_username', username.value)
    localStorage.setItem('prolific_last_password', password.value)

    // Navigate using the service
    await NavigationService.afterProlificLogin(prolificParams.value)
  } catch (error) {
    console.error('Prolific login error:', error)
    errorMessage.value = error.message || 'An error occurred during Prolific sign-in'
  } finally {
    credentialLoading.value = false
  }
}
</script>

<style scoped>
.auth-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  max-width: 400px;
  width: 100%;
}

.trading-logo {
  width: 80%;
  height: 80%;
  vertical-align: middle;
  margin-left: 8px;
}
</style>
