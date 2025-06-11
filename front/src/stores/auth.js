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
  
  // Computed
  const isAuthenticated = computed(() => !!user.value)
  const prolificId = computed(() => 
    user.value?.isProlific ? user.value.prolificData?.PROLIFIC_PID || '' : ''
  )
  
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
      
      if (!response.data.data?.trader_id) {
        throw new Error('No trader ID received')
      }
      
      isAdmin.value = response.data.data.is_admin || false
      traderId.value = response.data.data.trader_id
      marketId.value = response.data.data.market_id
      isPersisted.value = false
      
      if (response.data.data.prolific_token) {
        prolificToken.value = response.data.data.prolific_token
      }
      
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
    if (loginInProgress.value || (user.value?.uid === firebaseUser.uid && traderId.value)) {
      return
    }
    
    try {
      loginInProgress.value = true
      const response = await axios.post('/user/login')
      
      if (!response.data.data.trader_id) {
        if (!isAutoLogin) {
          // Retry once for manual login
          await new Promise(resolve => setTimeout(resolve, 1000))
          const retryResponse = await axios.post('/user/login')
          if (!retryResponse.data.data.trader_id) {
            throw new Error('Failed to get trader ID')
          }
          Object.assign(response, retryResponse)
        } else {
          throw new Error('Failed to get trader ID')
        }
      }
      
      if (firebaseUser.uid === auth.currentUser?.uid) {
        user.value = firebaseUser
        isAdmin.value = response.data.data.is_admin
        traderId.value = response.data.data.trader_id
        marketId.value = response.data.data.market_id
        
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
  
  function logout() {
    user.value = null
    isAdmin.value = false
    traderId.value = null
    marketId.value = null
    isPersisted.value = false
    isInitialized.value = false
    loginInProgress.value = false
    prolificToken.value = null
    
    localStorage.removeItem('auth')
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
    
    // Computed
    isAuthenticated,
    prolificId,
    
    // Actions
    initializeAuth,
    prolificLogin,
    login,
    adminLogin,
    logout
  }
}) 