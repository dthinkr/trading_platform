import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/",
    name: "Auth",
    component: () => import("@/components/Auth.vue"),
    props: (route) => ({
      prolificPID: route.query.PROLIFIC_PID,
      studyID: route.query.STUDY_ID,
      sessionID: route.query.SESSION_ID
    })
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/components/Auth.vue")
  },
  {
    path: "/onboarding",
    name: "Onboarding",
    component: () => import("@/components/OnboardingFlow.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/market-creator",
    name: "MarketCreator",
    component: () => import("@/components/market/MarketCreator.vue"),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/waiting-room",
    name: "WaitingRoom",
    component: () => import("@/components/WaitingRoom.vue"),
    meta: { requiresAuth: true, requiresOnboarding: true }
  },
  {
    path: "/trading",
    name: "Trading",
    component: () => import("@/components/TradingDashboard.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/summary/:traderUuid",
    name: "Summary",
    component: () => import("@/components/market/MarketSummary.vue"),
    props: true,
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);
  const requiresOnboarding = to.matched.some(record => record.meta.requiresOnboarding);

  // Allow Prolific parameters through
  const hasProlificParams = to.query.PROLIFIC_PID && to.query.STUDY_ID && to.query.SESSION_ID;
  if (hasProlificParams) {
    console.log('Router: Prolific params detected, allowing navigation');
    next();
    return;
  }

  // Check authentication
  if (requiresAuth && !authStore.isAuthenticated) {
    console.log('Router: Authentication required, redirecting to auth');
    next('/');
  } else if (requiresAdmin && !authStore.isAdmin) {
    console.log('Router: Admin access required, redirecting to auth');
    next('/'); 
  } else if (requiresOnboarding && !authStore.hasCompletedOnboarding) {
    console.log('Router: Onboarding required, redirecting to onboarding');
    next('/onboarding');
  } else {
    next();
  }
});

export default router;
