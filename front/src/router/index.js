import { createRouter, createWebHistory } from "vue-router";
import routeGraph from './routeGraph';
import { useTraderStore } from "@/store/app";

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
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const traderStore = useTraderStore();

  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!traderStore.isAuthenticated) {
      next({ name: 'Register' });
    } else {
      next();
    }
  } else {
    next();
  }
});

export default router;