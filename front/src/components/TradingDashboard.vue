<template>
  <v-app class="trading-system">
    <v-app-bar app elevation="2" color="primary" dark>
      <v-container fluid class="pa-0 fill-height">
        <v-row no-gutters class="fill-height">
          <!-- Left column: Timer -->
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

          <!-- Middle column: VWAP, PnL, Shares, Cash, Traders -->
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

          <!-- Right column: Goal Message -->
          <v-col cols="12" md="5" class="d-flex align-center justify-end">
            <v-card v-if="goalMessage" outlined class="pa-2 mr-2 goal-message floating-card" :class="goalMessage.type === 'success' ? 'goal-success' : 'goal-warning'">
              <v-row no-gutters align="center">
                <v-col cols="auto" class="mr-2">
                  <v-icon :color="goalMessage.type === 'success' ? 'light-green darken-1' : 'amber darken-2'">
                    {{ goalMessage.type === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                  </v-icon>
                </v-col>
                <v-col>
                  <v-card-subtitle class="pa-0 text-caption goal-subtitle">Goal</v-card-subtitle>
                  <v-card-text class="pa-0 text-body-2 font-weight-medium goal-text">
                    {{ goalMessage.text }}
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
          <v-col cols="12" md="2" class="d-flex flex-column">
            <v-card v-for="(tool, toolIndex) in columns[0]" :key="toolIndex" 
                    :class="['flex-grow-1 mb-4 tool-card', `tool-card-row-${toolIndex + 1}`]" 
                    elevation="3">
              <v-card-title>{{ tool.title }}</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <component :is="tool.component" class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
          <v-col v-for="colIndex in [1, 2]" :key="colIndex" cols="12" md="5" class="d-flex flex-column">
            <v-card v-for="(tool, toolIndex) in columns[colIndex]" :key="toolIndex" 
                    :class="['flex-grow-1 mb-4 tool-card', `tool-card-row-${toolIndex + 1}`]" 
                    elevation="3">
              <v-card-title>{{ tool.title }}</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <component :is="tool.component" class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
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
const { formatNumber } = useFormatNumber();
const router = useRouter();
const store = useTraderStore();
const { 
  gameParams, 
  goalMessage, 
  shares, 
  cash, 
  sum_dinv, 
  initial_shares, 
  dayOver, 
  pnl, 
  vwap, 
  remainingTime, 
  isTradingStarted,
  currentHumanTraders,
  expectedHumanTraders,
  traderUuid // Add this
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
  const halfChange = Math.round(sum_dinv.value / 2); // Divide by 2 and round to nearest integer
  return halfChange >= 0 ? "+" + halfChange : halfChange.toString();
});

const finalizingDay = () => {
  if (traderUuid.value) {
    router.push({ name: "summary", params: { traderUuid: traderUuid.value } });
  } else {
    console.error('No trader UUID found');
    // Handle this error case, maybe redirect to login
    router.push({ name: "Register" });
  }
};

watch(
  remainingTime,
  (newValue) => {
    if (newValue !== null && newValue <= 0 && isTradingStarted.value) {
      finalizingDay();
    }
  }
);
</script>

<style scoped>
.trading-system {
  font-family: 'Roboto', sans-serif;
}

.tool-card {
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5 !important;
  transition: all 0.3s ease;
  overflow: hidden;
  height: calc(45% - 2px); /* Reduced height */
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
  overflow: auto;
  padding: 16px;
}

.fill-height {
  height: 100%;
}

/* Scaling styles */
.trading-system {
  transform: scale(0.9);
  transform-origin: top;
}

.trading-system > .v-application__wrap {
  height: 111.11%; /* 100% / 0.9 */
}

/* Adjust scrollbars if needed */
.trading-system ::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.trading-system ::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.3);
}

/* Adjust font sizes */
.tool-card .v-card__text {
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
}

/* Existing goal message styles remain unchanged */

/* Ensure equal height for rows */
.v-row {
  flex-wrap: nowrap;
}

.v-col {
  display: flex;
  flex-direction: column;
}

/* Adjust the width of the columns */
@media (min-width: 960px) {
  .v-col-md-2 {
    flex-basis: 16.666667% !important;
    max-width: 16.666667% !important;
  }

  .v-col-md-5 {
    flex-basis: 41.666667% !important;
    max-width: 41.666667% !important;
  }
}

/* Add these new styles */
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

.goal-subtitle {
  color: rgba(0, 0, 0, 0.6) !important;
}

.goal-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.goal-message:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
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

.tool-card-row-1 {
  height: calc(20% - 2px); /* First row height */
}

.tool-card-row-2 {
  height: calc(60% - 2px); /* Second row height */
}
</style>