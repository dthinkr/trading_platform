import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/api/axios'
import { auth } from '@/firebaseConfig'
import { onAuthStateChanged } from 'firebase/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const isAdmin = ref(false)
  const traderId = ref(null)
  const marketId = ref(null)
  const isInitialized = ref(false)
  const isPersisted = ref(false)
  const loginInProgress = ref(false)
  const prolificToken = ref(null)
  const onboardingCompleted = ref(false)
  
  // Computed
  const isAuthenticated = computed(() => !!user.value)
  const prolificId = computed(() => 
    user.value?.isProlific ? user.value.prolificData?.PROLIFIC_PID || '' : ''
  )
  const hasCompletedOnboarding = computed(() => onboardingCompleted.value)
  
  // Actions
  async function initializeAuth() {
    return new Promise((resolve) => {
      const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
        if (firebaseUser && !loginInProgress.value) {
          try {
            isPersisted.value = true
            await login(firebaseUser, true)
          } catch (error) {
            console.error('Auto-login failed:', error)
            user.value = null
            isPersisted.value = false
          }
        } else if (!firebaseUser) {
          user.value = null
          isPersisted.value = false
        }
        
        // Load onboarding status
        loadOnboardingStatus()
        
        isInitialized.value = true
        resolve()
        unsubscribe()
      })
    })
  }
  
  async function prolificLogin(prolificParams, credentials = null) {
    if (loginInProgress.value) {
      console.log('Login already in progress')
      return
    }
    
    try {
      loginInProgress.value = true
      console.log('Starting Prolific login with params:', prolificParams)
      
      // Create pseudo-user for Prolific
      const prolificPID = prolificParams.PROLIFIC_PID
      const pseudoUser = {
        uid: `prolific_${prolificPID}`,
        email: `${prolificPID}@prolific.co`,
        displayName: `Prolific User ${prolificPID}`,
        isProlific: true,
        prolificData: prolificParams
      }
      
      user.value = pseudoUser
      
      // API call with Prolific parameters
      const url = `/user/login?PROLIFIC_PID=${prolificParams.PROLIFIC_PID}&STUDY_ID=${prolificParams.STUDY_ID}&SESSION_ID=${prolificParams.SESSION_ID}`
      
      let requestBody = {}
      if (credentials?.username && credentials?.password) {
        requestBody = {
          username: credentials.username,
          password: credentials.password
        }
      }
      
      const response = await axios.post(url, requestBody)
      
      isAdmin.value = response.data.data.is_admin || false
      isPersisted.value = false
      
      if (response.data.data.prolific_token) {
        prolificToken.value = response.data.data.prolific_token
      }
      
      // Load onboarding status for Prolific users too
      loadOnboardingStatus()
      
      console.log('Prolific login successful')
    } catch (error) {
      console.error('Prolific login error:', error)
      user.value = null
      throw new Error(error.message || 'Failed to login with Prolific')
    } finally {
      loginInProgress.value = false
    }
  }
  
  async function login(firebaseUser, isAutoLogin = false) {
    if (loginInProgress.value || (user.value?.uid === firebaseUser.uid)) {
      return
    }
    
    try {
      loginInProgress.value = true
      const response = await axios.post('/user/login')
      
      if (firebaseUser.uid === auth.currentUser?.uid) {
        user.value = firebaseUser
        isAdmin.value = response.data.data.is_admin
        
        if (!isAutoLogin) {
          isPersisted.value = false
        }
      }
    } catch (error) {
      console.error('Login error:', error)
      throw new Error(error.message || 'Failed to login')
    } finally {
      loginInProgress.value = false
    }
  }
  
  async function adminLogin(firebaseUser) {
    try {
      const response = await axios.post('/admin/login')
      user.value = firebaseUser
      isAdmin.value = response.data.data.is_admin
    } catch (error) {
      console.error('Admin login error:', error)
      throw new Error(error.message || 'Failed to login as admin')
    }
  }
  
  async function completeOnboarding() {
    try {
      // Mark onboarding as completed
      onboardingCompleted.value = true
      
      // Save to localStorage for persistence
      localStorage.setItem('onboarding-completed', 'true')
      
      // Save to backend
      try {
        const response = await axios.post('/user/complete-onboarding')
        console.log('Onboarding completed successfully')
        return response.data.data
      } catch (error) {
        console.warn('Failed to save onboarding completion to backend:', error)
        // Don't throw - local completion is sufficient
      }
    } catch (error) {
      console.error('Failed to complete onboarding:', error)
      throw error
    }
  }

  async function joinWaitingRoom() {
    try {
      const response = await axios.post('/user/join-waiting-room')
      console.log('Waiting room response:', response.data)
      
      // If session is ready, store trader/market info
      if (response.data.data?.session_ready && response.data.data.trader_id) {
        traderId.value = response.data.data.trader_id
        marketId.value = response.data.data.market_id
      }
      
      return response.data
    } catch (error) {
      console.error('Error joining waiting room:', error)
      throw error
    }
  }

  async function getWaitingRoomStatus() {
    try {
      const response = await axios.get('/user/waiting-room-status')
      return response.data.data
    } catch (error) {
      console.error('Error getting waiting room status:', error)
      throw error
    }
  }
  
  function loadOnboardingStatus() {
    const completed = localStorage.getItem('onboarding-completed')
    onboardingCompleted.value = completed === 'true'
  }
  
  function logout() {
    user.value = null
    isAdmin.value = false
    traderId.value = null
    marketId.value = null
    isPersisted.value = false
    isInitialized.value = false
    loginInProgress.value = false
    prolificToken.value = null
    onboardingCompleted.value = false
    
    localStorage.removeItem('auth')
    localStorage.removeItem('onboarding-completed')
  }
  
  return {
    // State
    user,
    isAdmin,
    traderId,
    marketId,
    isInitialized,
    isPersisted,
    loginInProgress,
    prolificToken,
    onboardingCompleted,
    
    // Computed
    isAuthenticated,
    prolificId,
    hasCompletedOnboarding,
    
    // Actions
    initializeAuth,
    prolificLogin,
    login,
    adminLogin,
    logout,
    completeOnboarding,
    loadOnboardingStatus,
    joinWaitingRoom,
    getWaitingRoomStatus
  }
}) 