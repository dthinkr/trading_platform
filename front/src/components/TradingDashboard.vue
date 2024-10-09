<template>
  <div class="trading-dashboard">
    <v-app>
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
              <v-chip v-for="(item, index) in [
                { label: 'VWAP', value: formatNumber(vwap), icon: 'mdi-chart-line' },
                { label: 'PnL', value: pnl, icon: 'mdi-currency-usd' },
                { label: 'Shares', value: `${initial_shares} ${formatDelta}`, icon: 'mdi-file-document-outline' },
                { label: 'Cash', value: cash, icon: 'mdi-cash' },
                { label: 'Traders', value: `${currentHumanTraders} / ${expectedHumanTraders}`, icon: 'mdi-account-group' }
              ]" :key="index" class="mr-2" color="grey lighten-4">
                <v-icon left small color="deep-blue">{{ item.icon }}</v-icon>
                {{ item.label }}: {{ item.value }}
              </v-chip>
              <v-chip v-if="displayGoalMessage" :color="getGoalMessageClass" text-color="white" class="mr-2">
                <v-icon left small>{{ getGoalMessageIcon }}</v-icon>
                {{ displayGoalMessage.text }}
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
          <v-row>
            <v-col v-for="(columnTools, colIndex) in columns" :key="colIndex" :cols="12" :md="colIndex === 0 ? 2 : 5" class="d-flex flex-column">
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

import { onMounted, onUnmounted, ref } from 'vue';

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
    { title: "Order History", component: OrderHistory },
    { title: "Market Info", component: MarketMessages },
  ],
  [
    { title: "Buy-Sell Chart", component: BidAskDistribution },
    { title: "Active Orders", component: ActiveOrders },
  ],
  [
    { title: "Price History", component: PriceHistory },
    { title: "Trading Panel", component: PlaceOrder },
  ],
];

const formatDelta = computed(() => {
  if (sum_dinv.value == undefined) return "";
  const halfChange = Math.round(sum_dinv.value / 2);
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

const zoomLevel = ref(1);

const calculateZoom = () => {
  const targetWidth = 1600; // Target width for the design
  const targetHeight = 1000; // Target height for the design
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;

  const widthRatio = windowWidth / targetWidth;
  const heightRatio = windowHeight / targetHeight;

  // Use the smaller ratio to ensure the dashboard fits within the screen
  zoomLevel.value = Math.min(widthRatio, heightRatio, 1);
};

const handleResize = () => {
  calculateZoom();
};

onMounted(() => {
  calculateZoom();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

const isGoalAchieved = computed(() => {
  return goalMessage.value && goalMessage.value.type === 'success';
});

const goalType = computed(() => {
  if (goalMessage.value) {
    const goalText = goalMessage.value.text.toLowerCase();
    if (goalText.includes('buy')) return 'buy';
    if (goalText.includes('sell')) return 'sell';
    if (goalText.includes('0') || goalText.includes('zero')) return 'free';
  }
  return 'free';
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

const getGoalMessageClass = computed(() => {
  if (displayGoalMessage.value.type === 'success') return 'goal-success';
  if (displayGoalMessage.value.type === 'warning') return 'goal-warning';
  return 'goal-info';
});

const getGoalMessageIconColor = computed(() => {
  if (displayGoalMessage.value.type === 'success') return 'light-green darken-1';
  if (displayGoalMessage.value.type === 'warning') return 'amber darken-2';
  return 'blue darken-1';
});

const getGoalMessageIcon = computed(() => {
  if (displayGoalMessage.value.type === 'success') return 'mdi-check-circle';
  if (displayGoalMessage.value.type === 'warning') return 'mdi-alert-circle';
  return 'mdi-information';
});

// Add this function to get icons for each tool
const getToolIcon = (toolTitle) => {
  switch (toolTitle) {
    case 'Order History': return 'mdi-history';
    case 'Market Messages': return 'mdi-message-text';
    case 'Buy-Sell Distribution': return 'mdi-chart-bar';
    case 'Active Orders': return 'mdi-clipboard-text';
    case 'Price History': return 'mdi-chart-line';
    case 'Trading Panel': return 'mdi-cash-register';
    default: return 'mdi-help-circle';
  }
};
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
</style>