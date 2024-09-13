import { createRouter, createWebHistory } from "vue-router";
import { auth } from '@/firebaseConfig';  // Import Firebase auth

const routes = [
  {
    path: "/",
    redirect: "/register",
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/components/Auth.vue"),
  },
  {
    path: "/CreateTradingSession",
    name: "CreateTradingSession",
    component: () => import("@/components/session/SessionCreator.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/admin/:tradingSessionUUID",
    name: "admin",
    component: () => import("@/components/AdminPage.vue"),
    props: true,
  },
  {
    path: "/onboarding/:traderUuid/:duration?/:numRounds?",
    name: "onboarding",
    component: () => import("@/components/OnboardingWizard.vue"),
    props: true,
  },
  {
    path: "/trading/:traderUuid",
    name: "trading",
    component: () => import("@/components/TradingDashboard.vue"),
    props: true,
  },
  {
    path: "/summary/:traderUuid",
    name: "summary",
    component: () => import("@/components/session/SessionSummary.vue"),
    props: true,
  },
];

console.log('Routes:', routes);
console.log('Is array:', Array.isArray(routes));
console.log('Has forEach:', typeof routes.forEach === 'function');

const router = createRouter({
  history: createWebHistory('/trading/'),
  routes: Array.from(routes) // Explicitly create a new array
});

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const currentUser = auth.currentUser;

  if (requiresAuth && !currentUser) {
    next('/register');
  } else {
    next();
  }
});

export default router;