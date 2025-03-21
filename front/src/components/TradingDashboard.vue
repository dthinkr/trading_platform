<template>
  <div class="trading-dashboard" v-show="isInitialized">
    <v-app>
      <!-- Add error alert at the top -->
      <v-alert
        v-if="showErrorAlert"
        type="error"
        closable
        class="ma-4"
        style="position: fixed; top: 0; left: 50%; transform: translateX(-50%); z-index: 1000;"
      >
        Connection error. Please refresh the page.
        <v-btn
          color="white"
          variant="text"
          class="ml-4"
          @click="refreshPage"
        >
          Refresh Now
        </v-btn>
      </v-alert>

      <v-app-bar app elevation="2" color="white">
        <v-container fluid class="py-0 fill-height">
          <v-row align="center" no-gutters>
            <v-col cols="auto">
              <h1 class="text-h5 font-weight-bold primary--text">
                <v-icon left color="light-blue" large>mdi-chart-line</v-icon>
                Trading Dashboard
              </h1>
            </v-col>
            <v-spacer></v-spacer>
            <v-col cols="auto" class="d-flex align-center">
              <!-- Add role chip before other chips -->
              <v-chip class="mr-2" :color="roleColor" text-color="white">
                <v-icon left small>{{ roleIcon }}</v-icon>
                {{ roleDisplay.text }}
              </v-chip>
              <v-chip v-for="(item, index) in [
                // { label: 'VWAP', value: formatNumber(vwap), icon: 'mdi-chart-line' },
                { label: 'PnL', value: pnl, icon: 'mdi-cash-plus' },
                { label: 'Shares', value: `${initial_shares} ${formatDelta}`, icon: 'mdi-package-variant' },
                { label: 'Cash', value: cash, icon: 'mdi-cash-multiple' },
                { label: 'Traders', value: `${currentHumanTraders} / ${expectedHumanTraders}`, icon: 'mdi-account-multiple' }
              ]" :key="index" class="mr-2" color="grey lighten-4">
                <v-icon left small color="deep-blue">{{ item.icon }}</v-icon>
                <span class="black--text">{{ item.label }}: {{ item.value }}</span>
              </v-chip>
              <v-chip 
                v-if="hasGoal" 
                :color="getGoalMessageClass" 
                text-color="white" 
                class="mr-2 goal-chip"
              >
                <div class="d-flex align-center">
                  <v-icon left small>{{ getGoalMessageIcon }}</v-icon>
                  <span class="goal-type-text mr-2">{{ goalTypeText }}</span>
                </div>
                <v-progress-linear
                  :value="goalProgressPercentage"
                  :color="progressBarColor"
                  height="6"
                  rounded
                  striped
                  class="ml-2"
                ></v-progress-linear>
                <span class="progress-text ml-2">{{ Math.abs(goalProgress) }}/{{ Math.abs(goal) }}</span>
              </v-chip>
              <v-chip color="deep-blue" text-color="white">
                <v-icon left small>mdi-clock-outline</v-icon>
                <vue-countdown v-if="remainingTime" :time="remainingTime * 1000" v-slot="{ minutes, seconds }">
                  {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
                </vue-countdown>
                <span v-else>Waiting to start</span>
              </v-chip>
            </v-col>
          </v-row>
        </v-container>
      </v-app-bar>

      <v-main class="grey lighten-4">
        <v-container fluid class="pa-4">
          <!-- Modified waiting screen -->
          <v-row v-if="!isTradingStarted" justify="center" align="center" style="height: 80vh;">
            <v-col cols="12" md="6" class="text-center">
              <v-card elevation="2" class="pa-6">
                <v-card-title class="text-h4 mb-4">Waiting for Traders</v-card-title>
                <v-card-text>
                  <p class="text-h6 mb-4">
                    {{ currentHumanTraders }} out of {{ expectedHumanTraders }} traders have joined
                  </p>
                  <p class="subtitle-1 mb-4">
                    Your Role: 
                    <v-chip :color="roleColor" text-color="white" small>
                      <v-icon left small>{{ roleIcon }}</v-icon>
                      {{ roleDisplay.text }}
                    </v-chip>
                  </p>
                  <v-progress-circular
                    :size="70"
                    :width="7"
                    color="primary"
                    indeterminate
                  ></v-progress-circular>
                  <p class="text--secondary mt-4">
                    <v-icon small color="grey">mdi-refresh</v-icon>
                    If waiting too long, you can refresh the page to try again
                  </p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
          <v-row v-else>            <v-col v-for="(columnTools, colIndex) in columns" :key="colIndex" :cols="12" :md="colIndex === 0 ? 2 : 5" class="d-flex flex-column">
              <v-card v-for="(tool, toolIndex) in columnTools" :key="toolIndex" 
                      class="mb-4 tool-card" 
                      :class="{'price-history-card': tool.title === 'Price History'}"
                      elevation="2">
                <v-card-title class="headline">
                  <v-icon left color="deep-blue">{{ getToolIcon(tool.title) }}</v-icon>
                  {{ tool.title }}
                </v-card-title>
                <v-card-text class="pa-0">
                  <component :is="tool.component" :isGoalAchieved="isGoalAchieved" :goalType="goalType" />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </v-main>
    </v-app>
  </div>
</template>

<script setup>  
import BidAskDistribution from "@charts/BidAskDistribution.vue";
import PriceHistory from "@charts/PriceHistory.vue";
import PlaceOrder from "@trading/PlaceOrder.vue";
import OrderHistory from "@trading/OrderHistory.vue";
import ActiveOrders from "@trading/ActiveOrders.vue";
import MarketMessages from "@trading/MarketMessages.vue";

import { computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useFormatNumber } from "@/composables/utils";
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";

import { onMounted, onUnmounted, ref, onBeforeUnmount } from 'vue';
import { debounce } from 'lodash';

const { formatNumber } = useFormatNumber();
const router = useRouter();
const store = useTraderStore();
const { 
  goalMessage, 
  initial_shares, 
  pnl, 
  vwap, 
  remainingTime, 
  isTradingStarted,
  currentHumanTraders,
  expectedHumanTraders,
  traderUuid,
  cash,
  sum_dinv,
  activeOrders
} = storeToRefs(store);

const columns = [
  [
    { title: "Trades History", component: OrderHistory },
    { title: "Market Info", component: MarketMessages },
  ],
  [
    { title: "Buy-Sell Chart", component: BidAskDistribution },
    { title: "Passive Orders", component: ActiveOrders },
  ],
  [
    { title: "Price History", component: PriceHistory },
    { title: "Trading Panel", component: PlaceOrder },
  ],
];

const formatDelta = computed(() => {
  if (sum_dinv.value == undefined) return "";
  const halfChange = Math.round(sum_dinv.value);
  return halfChange >= 0 ? "+" + halfChange : halfChange.toString();
});

const finalizingDay = () => {
  if (traderUuid.value) {
    router.push({ name: "summary", params: { traderUuid: traderUuid.value } });
  } else {
    console.error('No trader UUID found');
    router.push({ name: "Register" });
  }
};

watch(remainingTime, (newValue) => {
  if (newValue !== null && newValue <= 0 && isTradingStarted.value) {
    finalizingDay();
  }
});

// Remove the calculateZoom function and replace with a fixed value
const zoomLevel = ref(0.95);  // Fixed 90% zoom

onMounted(async () => {
  // Apply zoom only once, using CSS transform instead of zoom
  document.body.style.transform = 'scale(0.95)';
  document.body.style.transformOrigin = 'top left';
  // Remove the zoom property as it can cause flickering in some browsers
  // document.body.style.zoom = zoomLevel.value;
  
  // Fetch user role
  try {
    const response = await fetch('/api/user/role', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    const data = await response.json();
    if (data.status === 'success') {
      userRole.value = data.data.role;
    }
  } catch (error) {
    console.error('Error fetching user role:', error);
  }

  // Start market timeout countdown if not started
  if (!isTradingStarted.value) {
    marketTimeoutInterval.value = setInterval(() => {
      if (marketTimeRemaining.value > 0) {
        marketTimeRemaining.value--;
      }
    }, 1000);
  }
});

onUnmounted(() => {
  // Remove other cleanup code if needed
});

// First, define the basic computed properties
const goal = computed(() => store.traderAttributes?.goal || 0);
const goalProgress = computed(() => store.traderAttributes?.goal_progress || 0);
const hasGoal = computed(() => goal.value !== 0);

// Then define the dependent computed properties
const isGoalAchieved = computed(() => {
  if (!hasGoal.value) return false;
  return Math.abs(goalProgress.value) >= Math.abs(goal.value);
});

const goalType = computed(() => {
  if (!hasGoal.value) return 'free';
  return goal.value > 0 ? 'buy' : 'sell';
});

const goalProgressPercentage = computed(() => {
  if (!hasGoal.value) return 0;
  const targetGoal = Math.abs(goal.value);
  const currentProgress = Math.abs(goalProgress.value);
  return Math.min((currentProgress / targetGoal) * 100, 100);
});

const goalProgressColor = computed(() => {
  if (isGoalAchieved.value) return 'light-green accent-4';
  return goal.value > 0 ? 'blue lighten-1' : 'red lighten-1';
});

const getGoalMessageClass = computed(() => {
  if (isGoalAchieved.value) return 'success-bg';
  return goal.value > 0 ? 'buy-bg' : 'sell-bg';
});

const getGoalMessageIcon = computed(() => {
  if (!hasGoal.value) return 'mdi-information';
  return goal.value > 0 ? 'mdi-arrow-up-bold' : 'mdi-arrow-down-bold';
});

const displayGoalMessage = computed(() => {
  if (!goalMessage.value) {
    return {
      type: 'info',
      text: 'You can freely trade. Your goal is to profit from the market.'
    };
  }
  return goalMessage.value;
});

// Add this function to cancel all active orders
const cancelAllActiveOrders = () => {
  activeOrders.value.forEach(order => {
    store.cancelOrder(order.id);
  });
};

// Watch for changes in isGoalAchieved
watch(isGoalAchieved, (newValue) => {
  if (newValue) {
    cancelAllActiveOrders();
  }
});

// Add this function to get icons for each tool
const getToolIcon = (toolTitle) => {
  switch (toolTitle) {
    case 'Trades History': return 'mdi-history';
    case 'Market Info': return 'mdi-information';
    case 'Buy-Sell Chart': return 'mdi-chart-bar';
    case 'Passive Orders': return 'mdi-format-list-bulleted';
    case 'Price History': return 'mdi-chart-line';
    case 'Trading Panel': return 'mdi-cash-register';
    default: return 'mdi-help-circle';
  }
};

// Add these to your existing refs/computed
const userRole = ref('');
const marketTimeRemaining = ref(null); // Infinite timeout
const marketTimeoutInterval = ref(null);

// Add these computed properties
const roleDisplay = computed(() => {
  if (!hasGoal.value) {
    return {
      text: 'SPECULATOR',
      icon: 'mdi-account-search',
      color: 'teal'
    };
  }
  // Informed trader with different types
  if (goal.value > 0) {
    return {
      text: 'INFORMED (BUY)',
      icon: 'mdi-trending-up',
      color: 'indigo'
    };
  }
  return {
    text: 'INFORMED (SELL)',
    icon: 'mdi-trending-down',
    color: 'deep-purple'
  };
});

// Replace the existing roleColor and roleIcon computed properties
const roleColor = computed(() => roleDisplay.value.color);
const roleIcon = computed(() => roleDisplay.value.icon);

// Add watcher for trading started
watch(isTradingStarted, (newValue) => {
  if (newValue && marketTimeoutInterval.value) {
    clearInterval(marketTimeoutInterval.value);
    marketTimeRemaining.value = 0;
  }
});

// Add handler for market timeout
watch(marketTimeRemaining, (newValue) => {
  if (newValue === 0 && !isTradingStarted.value) {
    router.push({ name: 'Register', query: { error: 'Market timed out - not enough traders joined' } });
  }
});

const goalTypeText = computed(() => {
  if (!hasGoal.value) return 'FREE';
  return goal.value > 0 ? 'BUY' : 'SELL';
});

const progressBarColor = computed(() => {
  if (goalProgressPercentage.value === 100) {
    return 'light-green accent-3';
  }
  if (goalProgressPercentage.value > 75) {
    return 'light-green lighten-1';
  }
  if (goalProgressPercentage.value > 50) {
    return 'amber lighten-1';
  }
  if (goalProgressPercentage.value > 25) {
    return 'orange lighten-1';
  }
  return 'deep-orange lighten-1';
});

// Add this computed property
const allTradersReady = computed(() => {
  // This should be updated based on the WebSocket status updates
  // You'll need to track this in your store
  return store.allTradersReady;
});

// Add this computed property
const readyCount = computed(() => {
  return store.readyCount || 0;
});

// Add a computed property to track trader count changes
const traderCountDisplay = computed(() => {
  return `${currentHumanTraders.value} / ${expectedHumanTraders.value}`;
});

// Add a watcher to log changes (for debugging)
watch([currentHumanTraders, expectedHumanTraders], ([newCurrent, newExpected], [oldCurrent, oldExpected]) => {
  console.log(`Trader count updated: ${oldCurrent}/${oldExpected} -> ${newCurrent}/${newExpected}`);
});

// Add to your existing imports
//import { ref } from 'vue';


// Add these refs
const showErrorAlert = ref(false);

// Add this method
const refreshPage = () => {
  window.location.reload();
};

// Modify your store watch or WebSocket handler to include error handling
watch(() => store.ws, (newWs) => {
  if (newWs) {
    const debouncedHandler = debounce((event) => {
      try {
        if (typeof event.data === 'string' && 
            (event.data.startsWith('<!DOCTYPE') || event.data.startsWith('<html'))) {
          showErrorAlert.value = true;
          return;
        }
        const data = JSON.parse(event.data);
        // Your normal message handling...
      } catch (error) {
        if (error.message.includes("Unexpected token '<'")) {
          showErrorAlert.value = true;
        }
        console.error("WebSocket message error:", error);
      }
    }, 16); // Debounce to roughly one frame (60fps)

    newWs.addEventListener('message', debouncedHandler);
  }
}, { immediate: true });

// Add this computed property
const isInitialized = computed(() => {
  return Boolean(traderUuid.value && store.traderAttributes);
});
</script>

<style scoped>
.trading-dashboard {
  font-family: 'Inter', sans-serif;
}

.v-card {
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.v-card__title {
  font-size: 1.3rem;
  font-weight: 600;
  color: #2c3e50;
}

.headline {
  display: flex;
  align-items: center;
}

.tool-card {
  display: flex;
  flex-direction: column;
  background-color: white;
  transition: all 0.3s ease;
}

.tool-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.1);
}

.price-history-card {
  flex-grow: 1;
}

.goal-success {
  background-color: #4caf50 !important;
}

.goal-warning {
  background-color: #ff9800 !important;
}

.goal-info {
  background-color: #2196f3 !important;
}

.deep-blue {
  color: #1a237e !important;
}

.light-blue {
  color: #03a9f4 !important;
}

.v-chip {
  font-size: 0.85rem;
}

.black--text {
  color: black !important;
}

/* Add to existing styles */
.role-chip {
  font-weight: 500;
}

.market-timeout {
  color: #ff5252;
  font-weight: 500;
}

.goal-chip {
  min-width: 150px;
  height: 32px;
  display: flex;
  align-items: center;
  padding: 0 12px;
}

.goal-type-text {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  min-width: 35px;
}

.v-progress-linear {
  width: 60px;
  margin: 0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-text {
  font-size: 0.75rem;
  min-width: 32px;
  text-align: right;
  font-weight: 500;
}

/* Update the background colors */
.success-bg {
  background-color: #2e7d32 !important; /* Darker green */
}

.buy-bg {
  background-color: #1565c0 !important; /* Darker blue */
}

.sell-bg {
  background-color: #c62828 !important; /* Darker red */
}

/* Add to your existing styles */
.v-chip {
  font-weight: 500;
  letter-spacing: 0.5px;
}

/* Role-specific colors */
.informed-buy {
  background-color: #3949ab !important; /* Indigo */
}

.informed-sell {
  background-color: #673ab7 !important; /* Deep Purple */
}

.speculator {
  background-color: #00897b !important; /* Teal */
}

.v-alert {
  max-width: 500px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
</style>







