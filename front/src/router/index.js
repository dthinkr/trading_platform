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
    path: "/onboarding/:marketId/:traderUuid",
    component: () => import("@/components/UserLanding.vue"),
    props: true,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "welcome"
      },
      {
        path: "welcome",
        name: "welcome",
        component: () => import("@/components/pages/1.vue"),
      },
      {
        path: "platform",
        name: "platform",
        component: () => import("@/components/pages/2.vue"),
      },
      {
        path: "setup",
        name: "setup",
        component: () => import("@/components/pages/3.vue"),
      },
      {
        path: "earnings",
        name: "earnings",
        component: () => import("@/components/pages/4.vue"),
      },
      {
        path: "participants",
        name: "participants",
        component: () => import("@/components/pages/6.vue"),
      },
      {
        path: "questions",
        name: "questions",
        component: () => import("@/components/pages/7.vue"),
      },
      {
        path: "practice",
        name: "practice",
        component: () => import("@/components/pages/8.vue"),
      },
    ]
  },
  {
    path: "/MarketCreator",
    name: "MarketCreator",
    component: () => import("@/components/market/MarketCreator.vue"),
    props: true,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/trading/:traderUuid/:marketId",
    name: "trading",
    component: () => import("@/components/TradingDashboard.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/summary/:traderUuid",
    name: "summary",
    component: () => import("@/components/market/MarketSummary.vue"),
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

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/register');
  } else if (requiresAdmin && !authStore.isAdmin) {
    next('/'); // or to some 'unauthorized' page
  } else {
    next();
  }
});

export default router;
