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
    path: "/onboarding/:marketId/:traderUuid",
    name: "Onboarding",
    component: () => import("@/components/UserLanding.vue"),
    props: true,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "consent"
      },
      {
        path: "consent",
        name: "Consent",
        component: () => import("@/components/onboarding/ConsentPage.vue")
      },
      {
        path: "welcome",
        name: "Welcome",
        component: () => import("@/components/onboarding/WelcomePage.vue")
      },
      {
        path: "platform",
        name: "Platform",
        component: () => import("@/components/onboarding/PlatformPage.vue")
      },
      {
        path: "setup",
        name: "Setup",
        component: () => import("@/components/onboarding/SetupPage.vue")
      },
      {
        path: "earnings",
        name: "Earnings",
        component: () => import("@/components/onboarding/EarningsPage.vue")
      },
      {
        path: "participants",
        name: "Participants",
        component: () => import("@/components/onboarding/ParticipantsPage.vue")
      },
      {
        path: "questions",
        name: "Questions",
        component: () => import("@/components/onboarding/QuestionsPage.vue")
      },
      {
        path: "practice",
        name: "Practice",
        component: () => import("@/components/onboarding/PracticePage.vue")
      }
    ]
  },
  {
    path: "/market-creator",
    name: "MarketCreator",
    component: () => import("@/components/admin/MarketCreator.vue"),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/trading/:traderUuid/:marketId",
    name: "Trading",
    component: () => import("@/components/TradingDashboard.vue"),
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/summary/:traderUuid",
    name: "Summary",
    component: () => import("@/components/MarketSummary.vue"),
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
  } else {
    next();
  }
});

export default router;
