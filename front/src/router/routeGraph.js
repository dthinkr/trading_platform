import dagre from 'dagre';

// Import your components with new paths
import SessionCreator from "@session/SessionCreator.vue";
import TradingDashboard from "@/components/TradingDashboard.vue";
import AdminPage from "@/components/AdminPage.vue";
import SessionSummary from "@session/SessionSummary.vue";
import OnboardingWizard from "@/components/OnboardingWizard.vue";

// Create a new directed graph
const g = new dagre.graphlib.Graph();

// Set an object for the graph label
g.setGraph({});

// Default to assigning a new object as a label for each new edge.
g.setDefaultEdgeLabel(() => ({}));

// Add nodes to the graph
g.setNode("create", { component: SessionCreator, label: "Create Session" });
g.setNode("onboarding", { component: OnboardingWizard, label: "Trader Landing" });
g.setNode("trading", { component: TradingDashboard, label: "Trading System" });
g.setNode("summary", { component: SessionSummary, label: "Day Over" });
g.setNode("admin", { component: AdminPage, label: "Admin Page" });

// Add edges to the graph
g.setEdge("CreateTradingSession", "onboarding");
g.setEdge("CreateTradingSession", "admin");
g.setEdge("admin", "onboarding");
g.setEdge("onboarding", "trading");
g.setEdge("trading", "summary");
g.setEdge("summary", "CreateTradingSession");
g.setEdge("admin", "CreateTradingSession");

export default g;