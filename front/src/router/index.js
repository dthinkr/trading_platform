import { createRouter, createWebHistory } from "vue-router";
import routeGraph from './routeGraph';
import { useTraderStore } from "@/store/app";

const routes = [
  {
    path: "/",
    redirect: "/CreateTradingSession",
  },
  {
    path: "/CreateTradingSession",
    name: "CreateTradingSession",
    component: () => import("@/components/session/SessionCreator.vue"),
    props: true
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

  if (to.name === "trading" && !to.params.traderUuid) {
    next({ name: "CreateTradingSession" });
  } else if (to.name === "summary" && from.name !== "trading") {
    next({ name: "CreateTradingSession" });
  } else if (from.name === undefined || routeGraph.hasEdge(from.name, to.name) || to.name === from.name) {
    next();
  } else {
    console.warn(`Invalid navigation from ${from.name} to ${to.name}`);
    next(false);
  }
});

export default router;