import { createRouter, createWebHistory } from "vue-router";
import { auth } from '@/firebaseConfig';
import { useAuthStore } from '@/store/auth'; // Import the auth store

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
    path: "/SessionCreator",
    name: "SessionCreator",
    component: () => import("@/components/session/SessionCreator.vue"),
    props: true,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/admin/:tradingSessionUUID",
    name: "admin",
    component: () => import("@/components/AdminPage.vue"),
    props: true,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/onboarding/:traderUuid/:duration?/:numRounds?",
    name: "onboarding",
    component: () => import("@/components/OnboardingWizard.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/trading/:traderUuid",
    name: "trading",
    component: () => import("@/components/TradingDashboard.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/summary/:traderUuid",
    name: "summary",
    component: () => import("@/components/session/SessionSummary.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: routes
});

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);
  const currentUser = auth.currentUser;

  if (requiresAuth && !currentUser && !authStore.isAuthenticated) {
    next('/register');
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect non-admin users trying to access admin routes
    next('/'); // or to some 'unauthorized' page
  } else {
    next();
  }
});

export default router;