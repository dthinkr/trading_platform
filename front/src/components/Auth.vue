<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4" />
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>
            

            <!-- Loading indicator for Prolific authentication -->
            <div v-if="isProlificUser && isLoading" class="text-center my-6">
              <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
              <p class="text-subtitle-1 mt-4">Authenticating with Prolific...</p>
            </div>

            <!-- Prolific user credential form -->
            <div
              v-if="isProlificUser && !isLoading && !authStore.isAuthenticated"
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
                ></v-text-field>

                <v-text-field
                  v-model="password"
                  label="Password"
                  type="password"
                  required
                  variant="outlined"
                  class="mb-4"
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
            <template v-else>
              <p class="text-subtitle-1 mb-6">Sign in to access a trading market</p>

              <!-- Hidden buttons that will be auto-clicked -->
              <v-btn ref="autoSignInBtn" v-show="false" @click="signInWithGoogle"></v-btn>

              <v-btn ref="autoAdminSignInBtn" v-show="false" @click="adminSignInWithGoogle"></v-btn>

              <!-- Visible buttons for manual login -->
              <template v-if="!authStore.isAuthenticated">
                <v-btn block color="error" size="x-large" @click="signInWithGoogle" class="mb-4">
                  <v-icon start icon="mdi-google"></v-icon>
                  Sign in with Google
                </v-btn>

                <v-btn
                  block
                  color="primary"
                  size="x-large"
                  @click="adminSignInWithGoogle"
                  class="mb-4"
                >
                  <v-icon start icon="mdi-google"></v-icon>
                  Admin Sign in with Google
                </v-btn>
              </template>
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
import { ref, onMounted, defineProps } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { useAuthStore } from '@/store/auth'
import logo from '@/assets/trading_platform_logo.svg'

// Define props that can be passed from the router
const props = defineProps({
  prolificPID: String,
  studyID: String,
  sessionID: String,
})

const router = useRouter()
const route = useRoute()
const auth = getAuth()
const authStore = useAuthStore()

const errorMessage = ref('')
const autoSignInBtn = ref(null)
const autoAdminSignInBtn = ref(null)
const isProlificUser = ref(false)
const isLoading = ref(false)
const username = ref('')
const password = ref('')
const credentialLoading = ref(false)
const prolificParams = ref(null)

onMounted(async () => {
  // Check for Prolific parameters from props, URL, or localStorage
  let prolificPID = props.prolificPID || route.query.PROLIFIC_PID
  let studyID = props.studyID || route.query.STUDY_ID
  let sessionID = props.sessionID || route.query.SESSION_ID

  // Check if we have stored Prolific parameters for auto-login
  const storedProlificData = localStorage.getItem('prolific_auto_login')

  if (!prolificPID && !studyID && !sessionID && storedProlificData) {
    try {
      const parsedData = JSON.parse(storedProlificData)
      const timestamp = parsedData.timestamp || 0
      const currentTime = Date.now()
      const ageInMinutes = Math.floor((currentTime - timestamp) / (60 * 1000))

      // Only use stored data if it's less than 1 hour old
      if (currentTime - timestamp < 60 * 60 * 1000) {
        prolificPID = parsedData.PROLIFIC_PID
        studyID = parsedData.STUDY_ID
        sessionID = parsedData.SESSION_ID

        // Don't remove the data immediately, only after successful login
      } else {
        // Data is too old, clear it
        localStorage.removeItem('prolific_auto_login')
      }
    } catch (error) {
      console.error('Error parsing stored Prolific data:', error)
      localStorage.removeItem('prolific_auto_login')
    }
  }

  if (prolificPID && studyID && sessionID) {
    // We have Prolific parameters, store them and show credential form
    isProlificUser.value = true
    isLoading.value = false // Don't show loading, show credential form instead

    // Store Prolific parameters for later use
    prolificParams.value = {
      PROLIFIC_PID: prolificPID,
      STUDY_ID: studyID,
      SESSION_ID: sessionID,
    }

    // Check if we have stored credentials from previous login
    const lastUsername = localStorage.getItem('prolific_last_username')
    const lastPassword = localStorage.getItem('prolific_last_password')

    // Auto-fill the form with stored credentials if available
    if (lastUsername) {
      username.value = lastUsername
    }

    if (lastPassword) {
      password.value = lastPassword
    }
  } else {
    // Regular authentication flow
    await authStore.initializeAuth()

    // If user is already authenticated and has trader ID, auto-navigate
    if (authStore.isAuthenticated && authStore.traderId) {
      router.push({
        name: 'practice',
        params: {
          traderUuid: authStore.traderId,
          marketId: 'pending', // Market will be assigned when user clicks "Start Trading"
        },
      })
    }
  }
})

const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    const user = result.user

    await authStore.login(user)

    if (authStore.traderId) {
      // Market ID will be assigned when user clicks "Start Trading"
      const marketId = 'pending'
      
      // Check if this is a persisted login
      if (authStore.isPersisted) {
        router.push({
          name: 'practice', // Go directly to practice page
          params: {
            traderUuid: authStore.traderId,
            marketId: marketId,
          },
        })
      } else {
        router.push({
          name: 'consent', // New users start from consent page
          params: {
            traderUuid: authStore.traderId,
            marketId: marketId,
          },
        })
      }
    }
  } catch (error) {
    console.error('Google sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during sign-in'
  }
}

const adminSignInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    const user = result.user

    await authStore.adminLogin(user)

    if (authStore.isAdmin) {
      router.push('/MarketCreator')
    } else {
      errorMessage.value = 'You do not have admin privileges.'
    }
  } catch (error) {
    console.error('Admin Google sign-in error:', error)
    errorMessage.value = error.message || 'An error occurred during admin sign-in'
  }
}

// Handle Prolific credential login
const handleProlificCredentialLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = 'Please enter both username and password'
    return
  }

  credentialLoading.value = true
  isLoading.value = true

  try {
    // Pass credentials to the prolificLogin method
    await authStore.prolificLogin(prolificParams.value, {
      username: username.value,
      password: password.value,
    })

    // Now that login is successful, remove the stored Prolific data
    localStorage.removeItem('prolific_auto_login')

    // Store the username for future auto-fill
    localStorage.setItem('prolific_last_username', username.value)
    // Store the password for future auto-fill (only for Prolific users)
    localStorage.setItem('prolific_last_password', password.value)

    // Check if this is a continuation from the market summary
    const isNextMarket = localStorage.getItem('prolific_next_market') === 'true'
    if (isNextMarket) {
      localStorage.removeItem('prolific_next_market')
    }

    if (authStore.traderId) {
      // Market ID will be assigned when user clicks "Start Trading"
      const marketId = 'pending'
      
      let targetPage

      // Determine where to redirect based on different conditions
      if (isNextMarket) {
        // If coming from market summary, always go to practice page
        targetPage = 'practice'
      } else if (authStore.prolificUserHasCompletedOnboarding) {
        // If returning Prolific user, go to practice page
        targetPage = 'practice'
      } else {
        // First-time Prolific user, go to consent page
        targetPage = 'consent'
      }

      const redirectPath = `/onboarding/${marketId}/${authStore.traderId}/${targetPage}`

      // Use replace instead of push to avoid navigation issues
      router.replace(redirectPath)
    } else {
      console.error('Missing trader ID after Prolific login')
      errorMessage.value = 'Login successful but missing trader assignment'
    }
  } catch (error) {
    console.error('Prolific login error:', error)
    errorMessage.value = error.message || 'An error occurred during Prolific sign-in'
  } finally {
    credentialLoading.value = false
    isLoading.value = false
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

.admin-login-form {
  width: 100%;
}
</style>
