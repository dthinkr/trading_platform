// Router navigation guards
import { useAuthStore } from '@/store/auth'
import { useSessionStore } from '@/store/session'
import NavigationService from '@/services/navigation'

// Onboarding step routes in order
const ONBOARDING_ROUTES = ['consent', 'welcome', 'platform', 'setup', 'earnings', 'participants', 'questions', 'ready']

/**
 * Setup all navigation guards on the router
 */
export function setupGuards(router) {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()
    const sessionStore = useSessionStore()

    // 1. Handle Prolific params in URL - store them for later use
    if (to.query.PROLIFIC_PID && to.query.STUDY_ID && to.query.SESSION_ID) {
      sessionStore.setProlificParams({
        PROLIFIC_PID: to.query.PROLIFIC_PID,
        STUDY_ID: to.query.STUDY_ID,
        SESSION_ID: to.query.SESSION_ID,
      })
    }

    // 2. Guest-only routes (login page) - redirect authenticated users
    if (to.meta.requiresGuest && authStore.isAuthenticated) {
      const redirect = NavigationService.getRedirectForStatus(sessionStore.status)
      return next(redirect)
    }

    // 3. Auth required - redirect unauthenticated users to login
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      return next({ 
        name: 'auth', 
        query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined 
      })
    }

    // 4. Admin required
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      return next({ name: 'auth' })
    }

    // 5. Active market required (for trading page)
    if (to.meta.requiresActiveMarket) {
      if (sessionStore.status !== 'trading') {
        // Try to sync from backend first
        try {
          await sessionStore.syncFromBackend()
        } catch (e) {
          // Use local state
        }
        
        if (sessionStore.status !== 'trading') {
          const redirect = NavigationService.getRedirectForStatus(sessionStore.status)
          return next(redirect)
        }
      }
    }

    // 6. Onboarding step validation - prevent skipping steps
    if (to.meta.step !== undefined && to.meta.requiresAuth) {
      const targetStep = to.meta.step
      const currentStep = sessionStore.onboardingStep
      
      // Allow going back to any previous step
      // Allow going to current step or next step only
      if (targetStep > currentStep + 1) {
        // Trying to skip ahead - redirect to current step
        const allowedRoute = ONBOARDING_ROUTES[currentStep] || 'consent'
        return next({ name: allowedRoute })
      }
      
      // Update session step if navigating forward
      if (targetStep > currentStep) {
        sessionStore.setOnboardingStep(targetStep)
      }
    }

    // 7. Session sync for protected routes (non-blocking)
    if (to.meta.requiresSession && !sessionStore.isSyncing) {
      // Fire and forget - don't block navigation
      sessionStore.syncFromBackend().catch(() => {})
    }

    next()
  })

  // After each navigation, update session status if needed
  router.afterEach((to, from) => {
    const sessionStore = useSessionStore()
    
    // Update status based on current route
    if (to.name === 'trading') {
      sessionStore.setStatus('trading')
    } else if (to.name === 'summary') {
      sessionStore.setStatus('summary')
    } else if (to.name === 'ready') {
      sessionStore.setStatus('waiting')
    } else if (ONBOARDING_ROUTES.includes(to.name) && to.name !== 'ready') {
      sessionStore.setStatus('onboarding')
    }
  })
}

export default setupGuards
