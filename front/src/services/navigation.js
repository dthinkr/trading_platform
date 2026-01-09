// Centralized navigation service - all route transitions go through here
import router from '@/router'
import { useSessionStore } from '@/store/session'
import { useAuthStore } from '@/store/auth'
import { useTraderStore } from '@/store/app'
import { useWebSocketStore } from '@/store/websocket'

// Step name to route name mapping
const ONBOARDING_ROUTES = [
  'consent',
  'welcome', 
  'platform',
  'setup',
  'earnings',
  'participants',
  'questions',
  'ready'
]

export const NavigationService = {
  /**
   * Get the appropriate redirect based on session status
   */
  getRedirectForStatus(status) {
    switch (status) {
      case 'unauthenticated':
      case 'unknown':
        return { name: 'auth' }
      case 'authenticated':
      case 'onboarding':
        return { name: 'consent' }
      case 'waiting':
        return { name: 'ready' }
      case 'trading':
        return { name: 'trading' }
      case 'summary':
        return { name: 'summary' }
      case 'complete':
        return { name: 'summary' }
      default:
        return { name: 'auth' }
    }
  },

  /**
   * Navigate to the appropriate page based on current session state
   */
  async navigateToCurrentState() {
    const sessionStore = useSessionStore()
    const route = this.getRedirectForStatus(sessionStore.status)
    
    // If in onboarding, go to the correct step
    if (sessionStore.status === 'onboarding' || sessionStore.status === 'authenticated') {
      const stepRoute = ONBOARDING_ROUTES[sessionStore.onboardingStep] || 'consent'
      return router.push({ name: stepRoute })
    }
    
    return router.push(route)
  },

  /**
   * After successful login - determine where to send the user
   */
  async afterLogin() {
    const sessionStore = useSessionStore()
    
    try {
      await sessionStore.syncFromBackend()
    } catch (e) {
      // If sync fails, use local state
      console.warn('Failed to sync session from backend:', e)
    }
    
    // Determine destination based on state
    if (sessionStore.hasCompletedOnboarding) {
      sessionStore.setStatus('waiting')
      return router.push({ name: 'ready' })
    } else {
      sessionStore.setStatus('onboarding')
      const stepRoute = ONBOARDING_ROUTES[sessionStore.onboardingStep] || 'consent'
      return router.push({ name: stepRoute })
    }
  },

  /**
   * After Prolific login
   */
  async afterProlificLogin(prolificParams) {
    const sessionStore = useSessionStore()
    sessionStore.setProlificParams(prolificParams)
    return this.afterLogin()
  },

  /**
   * Navigate to next onboarding step
   */
  async nextOnboardingStep() {
    const sessionStore = useSessionStore()
    
    // Get current step from the current route, not from session store
    // This ensures we're always moving forward from where we actually are
    const currentRoute = router.currentRoute.value
    const currentRouteStep = currentRoute.meta?.step
    
    // Use the route's step if available, otherwise fall back to session store
    const currentStep = currentRouteStep !== undefined ? currentRouteStep : sessionStore.onboardingStep
    
    if (currentStep >= ONBOARDING_ROUTES.length - 1) {
      // Already at last step (ready)
      return
    }
    
    const nextStep = currentStep + 1
    const nextRoute = ONBOARDING_ROUTES[nextStep]
    
    // Update session store to the next step
    sessionStore.setOnboardingStep(nextStep)
    
    if (nextRoute) {
      return router.push({ name: nextRoute })
    }
  },

  /**
   * Navigate to previous onboarding step
   */
  async prevOnboardingStep() {
    const sessionStore = useSessionStore()
    
    // Get current step from the current route
    const currentRoute = router.currentRoute.value
    const currentRouteStep = currentRoute.meta?.step
    const currentStep = currentRouteStep !== undefined ? currentRouteStep : sessionStore.onboardingStep
    
    if (currentStep <= 0) {
      return
    }
    
    const prevStep = currentStep - 1
    const prevRoute = ONBOARDING_ROUTES[prevStep]
    
    // Note: Don't decrease the session step when going back
    // The session step represents the furthest point reached
    
    if (prevRoute) {
      return router.push({ name: prevRoute })
    }
  },

  /**
   * Navigate to specific onboarding step (for direct navigation)
   */
  async goToOnboardingStep(step) {
    const sessionStore = useSessionStore()
    
    // Can only go to steps we've completed or the next one
    if (step > sessionStore.onboardingStep + 1) {
      step = sessionStore.onboardingStep
    }
    
    if (step < 0) step = 0
    if (step >= ONBOARDING_ROUTES.length) step = ONBOARDING_ROUTES.length - 1
    
    sessionStore.setOnboardingStep(step)
    return router.push({ name: ONBOARDING_ROUTES[step] })
  },

  /**
   * When user clicks "Start Trading" from ready page
   */
  async startTrading() {
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()
    
    try {
      await traderStore.startTradingMarket()
      sessionStore.setStatus('waiting')
      // Navigation will happen via WebSocket 'market_started' event
      // or immediately if all traders are ready
    } catch (error) {
      console.error('Failed to start trading:', error)
      throw error
    }
  },

  /**
   * Called by WebSocket when market starts - navigate to trading
   */
  async onMarketStarted(marketId = null) {
    const sessionStore = useSessionStore()
    
    if (marketId) {
      sessionStore.marketId = marketId
    }
    sessionStore.setStatus('trading')
    
    return router.push({ name: 'trading' })
  },

  /**
   * When trading session ends - navigate to summary
   */
  async onTradingEnded() {
    const sessionStore = useSessionStore()
    const wsStore = useWebSocketStore()
    
    sessionStore.setStatus('summary')
    sessionStore.incrementMarketsCompleted()
    wsStore.disconnect()
    
    return router.push({ name: 'summary' })
  },

  /**
   * Start next market (from summary page)
   */
  async startNextMarket() {
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()
    
    if (!sessionStore.canStartNewMarket) {
      return false
    }
    
    // Reset trader state for new market
    traderStore.clearStore()
    
    // Reset session for new market
    sessionStore.resetForNewMarket()
    
    return router.push({ name: 'ready' })
  },

  /**
   * Complete the study (for Prolific users)
   */
  async completeStudy() {
    const sessionStore = useSessionStore()
    sessionStore.setStatus('complete')
    // Stay on summary page - user will click Prolific redirect link
  },

  /**
   * Navigate to admin panel
   */
  async goToAdmin() {
    const authStore = useAuthStore()
    
    if (!authStore.isAdmin) {
      return router.push({ name: 'auth' })
    }
    
    return router.push({ name: 'admin' })
  },

  /**
   * Logout and reset all state
   */
  async logout() {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()
    const traderStore = useTraderStore()
    const wsStore = useWebSocketStore()
    
    // Disconnect WebSocket
    wsStore.disconnect()
    
    // Clear all stores
    traderStore.clearStore()
    sessionStore.reset()
    authStore.logout()
    
    // Clear any Prolific data
    localStorage.removeItem('prolific_params')
    localStorage.removeItem('prolific_auto_login')
    localStorage.removeItem('prolific_next_market')
    
    return router.push({ name: 'auth' })
  },

  /**
   * Handle recovery after page refresh
   */
  async recoverSession() {
    const sessionStore = useSessionStore()
    const authStore = useAuthStore()
    
    // Load Prolific params if they exist
    sessionStore.loadProlificParams()
    
    // If not authenticated, go to auth
    if (!authStore.isAuthenticated) {
      sessionStore.setStatus('unauthenticated')
      return { name: 'auth' }
    }
    
    // Try to sync from backend
    try {
      await sessionStore.syncFromBackend()
    } catch (e) {
      // Use persisted local state
      console.warn('Using persisted session state')
    }
    
    return this.getRedirectForStatus(sessionStore.status)
  }
}

export default NavigationService
