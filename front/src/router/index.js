import { createRouter, createWebHistory } from "vue-router";
import { useTraderStore } from "@/store/app";
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

// Add any additional routes from routeGraph that aren't already defined
routeGraph.nodes().forEach(node => {
  if (!routes.some(route => route.name === node)) {
    const nodeData = routeGraph.node(node);
    routes.push({
      path: `/${node}`,
      name: node,
      component: nodeData.component,
      props: true
    });
  }
});

const router = createRouter({
  history: createWebHistory('/trading/'),
  routes
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