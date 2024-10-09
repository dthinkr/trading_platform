<template>
  <div class="zoom-container">
    <v-app class="trading-system">
      <v-app-bar app elevation="2" color="primary" dark>
        <v-container fluid class="pa-0 fill-height">
          <v-row no-gutters class="fill-height">
            <!-- Timer -->
            <v-col cols="12" md="2" class="d-flex align-center">
              <v-card outlined class="mx-2 pa-2 floating-card timer-card" color="primary" dark>
                <template v-if="isTradingStarted">
                  <vue-countdown v-if="remainingTime" :time="remainingTime * 1000" v-slot="{ minutes, seconds }">
                    <v-chip color="accent" label class="font-weight-bold timer-chip">
                      {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
                    </v-chip>
                  </vue-countdown>
                </template>
                <template v-else>
                  <v-chip color="warning" label class="timer-chip">Waiting to start</v-chip>
                </template>
              </v-card>
            </v-col>

            <!-- VWAP, PnL, Shares, Cash, Traders -->
            <v-col cols="12" md="5" class="d-flex align-center justify-space-around">
              <v-card v-for="(item, index) in [
                { label: 'VWAP', value: formatNumber(vwap), icon: 'mdi-chart-line' },
                { label: 'PnL', value: pnl, icon: 'mdi-currency-usd' },
                { label: 'Shares', value: `${initial_shares} ${formatDelta}`, icon: 'mdi-file-document-outline' },
                { label: 'Cash', value: cash, icon: 'mdi-cash' },
                { label: 'Traders', value: `${currentHumanTraders} / ${expectedHumanTraders}`, icon: 'mdi-account-group' }
              ]" :key="index" outlined class="pa-2 floating-card" color="primary" dark>
                <v-row no-gutters align="center">
                  <v-col cols="auto" class="mr-2">
                    <v-icon>{{ item.icon }}</v-icon>
                  </v-col>
                  <v-col>
                    <v-card-subtitle class="pa-0 text-caption white--text">{{ item.label }}</v-card-subtitle>
                    <v-card-text class="pa-0 text-body-1 font-weight-bold white--text">{{ item.value }}</v-card-text>
                  </v-col>
                </v-row>
              </v-card>
            </v-col>

            <!-- Goal Message -->
            <v-col cols="12" md="5" class="d-flex align-center justify-end">
              <v-card v-if="displayGoalMessage" outlined class="pa-2 mr-2 goal-message floating-card" :class="getGoalMessageClass">
                <v-row no-gutters align="center">
                  <v-col cols="auto" class="mr-2">
                    <v-icon :color="getGoalMessageIconColor">
                      {{ getGoalMessageIcon }}
                    </v-icon>
                  </v-col>
                  <v-col>
                    <v-card-subtitle class="pa-0 text-caption goal-subtitle">Goal</v-card-subtitle>
                    <v-card-text class="pa-0 text-body-2 font-weight-medium goal-text">
                      {{ displayGoalMessage.text }}
                    </v-card-text>
                  </v-col>
                </v-row>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </v-app-bar>

      <v-main>
        <v-container fluid class="pa-4 fill-height">
          <v-row class="fill-height">
            <v-col v-for="(columnTools, colIndex) in columns" :key="colIndex" :cols="12" :md="colIndex === 0 ? 2 : 5" class="d-flex flex-column">
              <v-card v-for="(tool, toolIndex) in columnTools" :key="toolIndex" 
                      :class="['mb-4 tool-card', `tool-card-row-${toolIndex + 1}`, {'price-history-card': tool.title === 'Price History'}]" 
                      elevation="3">
                <v-card-title>{{ tool.title }}</v-card-title>
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
    { title: "Market Messages", component: MarketMessages },
  ],
  [
    { title: "Buy-Sell Distribution", component: BidAskDistribution },
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
</script>

<style scoped>
.zoom-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.trading-system {
  transform-origin: center center;
  transition: transform 0.3s ease;
}

.trading-system {
  font-family: 'Roboto', sans-serif;
}

.tool-card {
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5 !important;
  transition: all 0.3s ease;
  overflow: hidden;
  height: auto;
  min-height: 0; /* Remove minimum height */
}

.tool-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.tool-card .v-card__title {
  background-color: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  padding: 12px 16px;
  font-size: 1.1rem !important;
  line-height: 1.4 !important;
}

.tool-card .v-card__text {
  flex-grow: 1;
  overflow: visible; /* Change from auto to visible */
  padding: 16px;
  display: flex;
  flex-direction: column;
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
}

.tool-card .v-card__text > * {
  flex-grow: 0; /* Change from 1 to 0 */
  min-height: 0;
}

.fill-height {
  height: 100%;
}

.v-row {
  flex-wrap: nowrap;
}

.v-col {
  display: flex;
  flex-direction: column;
}

.v-app-bar .v-container {
  max-width: 100%;
}

.floating-card {
  transition: all 0.3s ease;
  background-color: rgba(255, 255, 255, 0.1) !important;
  backdrop-filter: blur(10px);
}

.floating-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.goal-message {
  background-color: white !important;
  transition: all 0.3s ease;
}

.goal-success {
  border-left: 4px solid #7CB342;
}

.goal-warning {
  border-left: 4px solid #FFB300;
}

.goal-info {
  border-left: 4px solid #2196F3;
}

.goal-subtitle {
  color: rgba(0, 0, 0, 0.6) !important;
}

.goal-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.timer-card {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.timer-chip {
  font-size: 1.2rem !important;
  padding: 0 16px !important;
}

.tool-card-row-1,
.tool-card-row-2 {
  flex-grow: 0; /* Change from 1 and 3 to 0 */
  min-height: 0; /* Remove minimum height */
}

.price-history-card {
  flex-grow: 0 !important; /* Change from 5 to 0 */
  min-height: 0 !important; /* Remove minimum height */
}

.price-history-card + .tool-card {
  flex-grow: 0;
  min-height: 0;
}

@media (max-width: 960px) {
  .tool-card-row-1,
  .tool-card-row-2,
  .price-history-card {
    min-height: 0; /* Remove minimum height */
  }
}

.v-main__wrap {
  display: flex;
  flex-direction: column;
}

.v-main__wrap > .container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.v-main__wrap > .container > .row {
  flex-grow: 1;
}

.v-card__text > div {
  width: 100%;
  height: 100%;
}
</style>

<style>
.trading-system {
  transform: scale(v-bind(zoomLevel));
  width: calc(100vw / v-bind(zoomLevel));
  height: calc(100vh / v-bind(zoomLevel));
}
</style>