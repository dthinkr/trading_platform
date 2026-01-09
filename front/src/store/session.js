// Session state management - single source of truth for user flow state
import { defineStore } from 'pinia'
import axios from '@/api/axios'

export const useSessionStore = defineStore('session', {
  state: () => ({
    // Core session state
    // 'unknown' | 'unauthenticated' | 'authenticated' | 'onboarding' | 'waiting' | 'trading' | 'summary' | 'complete'
    status: 'unknown',
    
    // IDs
    traderId: null,
    marketId: null,
    
    // Onboarding progress (0-7, where 7 = ready to trade)
    onboardingStep: 0,
    hasCompletedOnboarding: false,
    
    // Market progress
    marketsCompleted: 0,
    maxMarkets: 4,
    
    // Flags
    isRecovering: false,
    isSyncing: false,
    lastSyncTime: null,
    
    // Prolific-specific
    prolificParams: null,
  }),

  getters: {
    canTrade: (state) => state.status === 'trading',
    canStartNewMarket: (state) => state.marketsCompleted < state.maxMarkets,
    isLastMarket: (state) => state.marketsCompleted >= state.maxMarkets,
    isProlificUser: (state) => !!state.prolificParams,
    
    // Get the route name for current onboarding step
    currentOnboardingRoute: (state) => {
      const stepRoutes = ['consent', 'welcome', 'platform', 'setup', 'earnings', 'participants', 'questions', 'ready']
      return stepRoutes[state.onboardingStep] || 'consent'
    },
  },

  actions: {
    // Sync state from backend - call this on app init and after key transitions
    async syncFromBackend() {
      if (this.isSyncing) return this.status
      
      try {
        this.isSyncing = true
        const response = await axios.get('/session/status')
        const data = response.data.data || response.data
        
        this.$patch({
          status: data.status || 'authenticated',
          traderId: data.trader_id,
          marketId: data.market_id,
          onboardingStep: data.onboarding_step || 0,
          hasCompletedOnboarding: (data.onboarding_step || 0) >= 7,
          marketsCompleted: data.markets_completed || 0,
          maxMarkets: data.max_markets || 4,
          lastSyncTime: Date.now(),
        })
        
        this.saveToLocalStorage()
        return this.status
      } catch (error) {
        if (error.response?.status === 401) {
          this.status = 'unauthenticated'
        }
        throw error
      } finally {
        this.isSyncing = false
      }
    },

    // Set status locally (for optimistic updates)
    setStatus(newStatus) {
      this.status = newStatus
      this.saveToLocalStorage()
    },

    // Update onboarding progress
    setOnboardingStep(step) {
      this.onboardingStep = step
      this.hasCompletedOnboarding = step >= 7
      this.saveToLocalStorage()
    },

    // Increment onboarding step
    advanceOnboarding() {
      if (this.onboardingStep < 7) {
        this.onboardingStep++
        this.hasCompletedOnboarding = this.onboardingStep >= 7
        this.saveToLocalStorage()
      }
    },

    // Store Prolific params
    setProlificParams(params) {
      this.prolificParams = params
      if (params) {
        localStorage.setItem('prolific_params', JSON.stringify({
          ...params,
          timestamp: Date.now()
        }))
      } else {
        localStorage.removeItem('prolific_params')
      }
    },

    // Load Prolific params from localStorage
    loadProlificParams() {
      try {
        const stored = localStorage.getItem('prolific_params')
        if (stored) {
          const parsed = JSON.parse(stored)
          // Check if params are less than 2 hours old
          if (Date.now() - parsed.timestamp < 2 * 60 * 60 * 1000) {
            this.prolificParams = {
              PROLIFIC_PID: parsed.PROLIFIC_PID,
              STUDY_ID: parsed.STUDY_ID,
              SESSION_ID: parsed.SESSION_ID,
            }
            return this.prolificParams
          } else {
            localStorage.removeItem('prolific_params')
          }
        }
      } catch (e) {
        localStorage.removeItem('prolific_params')
      }
      return null
    },

    // Called when market is completed
    incrementMarketsCompleted() {
      this.marketsCompleted++
      this.saveToLocalStorage()
    },

    // Reset for new market
    resetForNewMarket() {
      this.marketId = null
      this.status = 'waiting'
      this.saveToLocalStorage()
    },

    // Full reset (logout)
    reset() {
      this.$patch({
        status: 'unauthenticated',
        traderId: null,
        marketId: null,
        onboardingStep: 0,
        hasCompletedOnboarding: false,
        marketsCompleted: 0,
        isRecovering: false,
        isSyncing: false,
        lastSyncTime: null,
        prolificParams: null,
      })
      localStorage.removeItem('prolific_params')
      this.saveToLocalStorage()
    },

    // Manual localStorage persistence (since pinia-plugin-persistedstate may not be installed)
    saveToLocalStorage() {
      const dataToSave = {
        traderId: this.traderId,
        marketId: this.marketId,
        status: this.status,
        onboardingStep: this.onboardingStep,
        hasCompletedOnboarding: this.hasCompletedOnboarding,
        marketsCompleted: this.marketsCompleted,
        maxMarkets: this.maxMarkets,
        prolificParams: this.prolificParams,
      }
      localStorage.setItem('session_store', JSON.stringify(dataToSave))
    },

    // Load from localStorage on init
    loadFromLocalStorage() {
      try {
        const stored = localStorage.getItem('session_store')
        if (stored) {
          const data = JSON.parse(stored)
          this.$patch(data)
        }
      } catch (e) {
        console.warn('Failed to load session from localStorage:', e)
      }
    },
  },

  // Note: If pinia-plugin-persistedstate is installed, this will work automatically
  // Otherwise, call saveToLocalStorage() manually after state changes
  persist: {
    enabled: true,
    strategies: [{
      storage: localStorage,
      paths: [
        'traderId',
        'marketId', 
        'status',
        'onboardingStep',
        'hasCompletedOnboarding',
        'marketsCompleted',
        'maxMarkets',
        'prolificParams',
      ]
    }]
  }
})
