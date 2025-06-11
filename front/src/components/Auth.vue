<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div class="card">
        <div class="card-body text-center">
          <!-- Logo and Header -->
          <div class="mb-8">
            <div class="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100">
              <ChartBarIcon class="h-6 w-6 text-blue-600" aria-hidden="true" />
            </div>
            <h1 class="mt-4 text-3xl font-bold text-neutral-900">Trading Platform</h1>
            <p class="mt-2 text-neutral-600">Sign in to access your trading account</p>
          </div>

          <!-- Loading State for Prolific -->
          <div v-if="isProlificUser && isLoading" class="py-8">
            <div class="flex flex-col items-center space-y-4">
              <div class="spinner h-8 w-8 text-blue-600"></div>
              <p class="text-neutral-600">Authenticating with Prolific...</p>
            </div>
          </div>

          <!-- Prolific Credential Form -->
          <div v-else-if="isProlificUser && !isLoading && !authStore.isAuthenticated" class="space-y-6">
            <h2 class="text-xl font-semibold text-neutral-900">Enter Your Credentials</h2>
            <p class="text-sm text-neutral-600">Please enter your username and password to continue</p>
            
            <form @submit.prevent="handleProlificCredentialLogin" class="space-y-4">
              <div>
                <label for="username" class="form-label">Username</label>
                <input
                  id="username"
                  v-model="username"
                  type="text"
                  required
                  class="form-input"
                  placeholder="Enter your username"
                  aria-describedby="username-help"
                />
              </div>
              
              <div>
                <label for="password" class="form-label">Password</label>
                <input
                  id="password"
                  v-model="password"
                  type="password"
                  required
                  class="form-input"
                  placeholder="Enter your password"
                  aria-describedby="password-help"
                />
              </div>
              
              <button 
                type="submit" 
                :disabled="credentialLoading || !username || !password"
                class="btn-primary w-full"
              >
                <span v-if="credentialLoading" class="flex items-center justify-center">
                  <div class="spinner h-4 w-4 mr-2"></div>
                  Signing in...
                </span>
                <span v-else>Sign In</span>
              </button>
            </form>
          </div>

          <!-- Regular Authentication -->
          <div v-else-if="!authStore.isAuthenticated" class="space-y-4">
            <button 
              @click="signInWithGoogle"
              class="w-full flex items-center justify-center px-4 py-3 border border-transparent rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors duration-200"
            >
              <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign in with Google
            </button>
            
            <button 
              @click="adminSignInWithGoogle"
              class="btn-primary w-full"
            >
              <UserIcon class="h-4 w-4 mr-2" aria-hidden="true" />
              Admin Sign in with Google
            </button>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="mt-4">
            <div class="rounded-md bg-red-50 p-4" role="alert">
              <div class="flex">
                <ExclamationTriangleIcon class="h-5 w-5 text-red-400" aria-hidden="true" />
                <div class="ml-3">
                  <h3 class="text-sm font-medium text-red-800">Error</h3>
                  <div class="mt-2 text-sm text-red-700">
                    {{ errorMessage }}
                  </div>
                  <div class="mt-4">
                    <button 
                      @click="errorMessage = ''"
                      class="btn-secondary text-xs"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { useAuthStore } from '@/stores/auth'
import { 
  ChartBarIcon, 
  UserIcon, 
  ExclamationTriangleIcon 
} from '@heroicons/vue/24/outline'

// Props
const props = defineProps({
  prolificPID: String,
  studyID: String,
  sessionID: String
})

// Composables
const router = useRouter()
const route = useRoute()
const auth = getAuth()
const authStore = useAuthStore()

// State
const errorMessage = ref('')
const isProlificUser = ref(false)
const isLoading = ref(false)
const username = ref('')
const password = ref('')
const credentialLoading = ref(false)
const prolificParams = ref(null)

// Methods
async function signInWithGoogle() {
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    
    await authStore.login(result.user)
    
    if (authStore.isAuthenticated) {
      if (authStore.traderId && authStore.marketId) {
        router.push({
          name: 'onboarding',
          params: {
            traderUuid: authStore.traderId,
            marketId: authStore.marketId
          }
        })
      } else {
        router.push({ name: 'register' })
      }
    }
  } catch (error) {
    console.error('Google sign-in error:', error)
    errorMessage.value = error.message || 'Failed to sign in with Google'
  }
}

async function adminSignInWithGoogle() {
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    
    await authStore.adminLogin(result.user)
    
    if (authStore.isAuthenticated && authStore.isAdmin) {
      router.push({ name: 'MarketCreator' })
    } else {
      errorMessage.value = 'Admin access denied'
    }
  } catch (error) {
    console.error('Admin Google sign-in error:', error)
    errorMessage.value = error.message || 'Failed to sign in as admin'
  }
}

async function handleProlificCredentialLogin() {
  if (!prolificParams.value) {
    errorMessage.value = 'Prolific parameters missing'
    return
  }
  
  try {
    credentialLoading.value = true
    
    await authStore.prolificLogin(prolificParams.value, {
      username: username.value,
      password: password.value
    })
    
    if (authStore.isAuthenticated) {
      // Store credentials for future use
      localStorage.setItem('prolific_last_username', username.value)
      localStorage.setItem('prolific_last_password', password.value)
      
      // Navigate to onboarding
      router.push({
        name: 'onboarding',
        params: {
          traderUuid: authStore.traderId,
          marketId: authStore.marketId
        }
      })
    }
  } catch (error) {
    console.error('Prolific credential login error:', error)
    errorMessage.value = error.message || 'Invalid credentials'
  } finally {
    credentialLoading.value = false
  }
}

// Lifecycle
onMounted(async () => {
  console.log('Auth component mounted at path:', route.path)
  
  // Check for Prolific parameters
  let prolificPID = props.prolificPID || route.query.PROLIFIC_PID
  let studyID = props.studyID || route.query.STUDY_ID
  let sessionID = props.sessionID || route.query.SESSION_ID
  
  // Check localStorage for stored Prolific data
  if (!prolificPID && !studyID && !sessionID) {
    const storedProlificData = localStorage.getItem('prolific_auto_login')
    if (storedProlificData) {
      try {
        const parsedData = JSON.parse(storedProlificData)
        const currentTime = Date.now()
        
        // Only use if less than 1 hour old
        if (currentTime - parsedData.timestamp < 60 * 60 * 1000) {
          prolificPID = parsedData.PROLIFIC_PID
          studyID = parsedData.STUDY_ID
          sessionID = parsedData.SESSION_ID
        } else {
          localStorage.removeItem('prolific_auto_login')
        }
      } catch (error) {
        console.error('Error parsing stored Prolific data:', error)
        localStorage.removeItem('prolific_auto_login')
      }
    }
  }
  
  if (prolificPID && studyID && sessionID) {
    isProlificUser.value = true
    isLoading.value = false
    
    prolificParams.value = {
      PROLIFIC_PID: prolificPID,
      STUDY_ID: studyID,
      SESSION_ID: sessionID
    }
    
    // Auto-fill stored credentials
    const lastUsername = localStorage.getItem('prolific_last_username')
    if (lastUsername) {
      username.value = lastUsername
    }
  }
})
</script>

<style scoped>
/* Any component-specific styles */
</style>
