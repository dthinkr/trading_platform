<template>
  <v-app class="trading-system">
    <v-app-bar app elevation="2" color="primary" dark>
      <v-container class="py-0 fill-height">
        <v-row align="center" no-gutters>
          <!-- Timer -->
          <v-col cols="auto">
            <v-card class="mx-3 pa-2" elevation="0" color="primary" dark>
              <template v-if="isTradingStarted">
                <vue-countdown v-if="remainingTime" :time="remainingTime * 1000" v-slot="{ minutes, seconds }">
                  <v-chip color="accent" label class="font-weight-bold">
                    {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
                  </v-chip>
                </vue-countdown>
              </template>
              <template v-else>
                <v-chip color="warning" label>Waiting to start</v-chip>
              </template>
            </v-card>
          </v-col>

          <v-spacer></v-spacer>

          <!-- Trader count -->
          <v-col cols="auto">
            <v-card outlined class="pa-2" color="primary" dark>
              <v-row no-gutters align="center">
                <v-col cols="auto" class="mr-2">
                  <v-icon>mdi-account-group</v-icon>
                </v-col>
                <v-col>
                  <v-card-subtitle class="pa-0 text-caption white--text">Traders</v-card-subtitle>
                  <v-card-text class="pa-0 text-body-1 font-weight-bold white--text">
                    {{ currentHumanTraders }} / {{ expectedHumanTraders }}
                  </v-card-text>
                </v-col>
              </v-row>
            </v-card>
          </v-col>

          <v-spacer></v-spacer>

          <!-- VWAP, PnL, Shares, Cash -->
          <v-col cols="auto">
            <v-row no-gutters>
              <v-col v-for="(item, index) in [
                { label: 'VWAP', value: formatNumber(vwap), icon: 'mdi-chart-line' },
                { label: 'PnL', value: pnl, icon: 'mdi-currency-usd' },
                { label: 'Shares', value: `${initial_shares} ${formatDelta}`, icon: 'mdi-file-document-outline' },
                { label: 'Cash', value: cash, icon: 'mdi-cash' }
              ]" :key="index" cols="auto" class="mx-2">
                <v-card outlined class="pa-2" color="primary" dark>
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
            </v-row>
          </v-col>

          <!-- Add a spacer to push the goal to the right -->
          <v-spacer></v-spacer>

          <!-- Goal Message -->
          <v-col cols="auto" v-if="goalMessage">
            <v-card outlined class="pa-2 mr-2 goal-message" :class="goalMessage.type === 'success' ? 'goal-success' : 'goal-warning'">
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

    <v-main class="grey lighten-4">
      <v-container fluid class="pa-6">
        <v-row class="fill-height">
          <v-col cols="12" lg="6" class="d-flex">
            <v-card class="flex-grow-1 mb-6 chart-card" elevation="3">
              <v-card-title>Buy-Sell Distribution</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <BidAskDistribution class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" lg="6" class="d-flex">
            <v-card class="flex-grow-1 mb-6 chart-card" elevation="3">
              <v-card-title>Price History</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <PriceHistory class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-row class="fill-height">
          <v-col cols="12" lg="6" class="d-flex">
            <v-card class="flex-grow-1 mb-6 chart-card" elevation="3">
              <v-card-title>Active Orders</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <ActiveOrders class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" lg="6" class="d-flex">
            <v-card class="flex-grow-1 mb-6 chart-card" elevation="3">
              <v-card-title>Trading Panel</v-card-title>
              <v-card-text class="pa-0 fill-height">
                <PlaceOrder class="fill-height" />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
    <v-navigation-drawer app right width="350" permanent class="elevation-4">
      <v-container fluid class="pa-4">
        <MarketMessages class="mb-6" />
        <OrderHistory />
      </v-container>
    </v-navigation-drawer>
  </v-app>
</template>

<script setup>
const props = defineProps({
  traderUuid: String,
});

// Updated imports
import BidAskDistribution from "@charts/BidAskDistribution.vue";
import PriceHistory from "@charts/PriceHistory.vue";
import PlaceOrder from "@trading/PlaceOrder.vue";
import OrderHistory from "@trading/OrderHistory.vue";
import ActiveOrders from "@trading/ActiveOrders.vue";
import MarketMessages from "@trading/MarketMessages.vue";

import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useFormatNumber } from "@/composables/utils";

const { formatNumber } = useFormatNumber();
const router = useRouter();
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";
import { watch } from "vue";
// Remove this line:
// const { initializeTrader } = useTraderStore();
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
  expectedHumanTraders
} = storeToRefs(useTraderStore());

// Remove this onMounted hook:
// onMounted(() => {
//   initializeTrader(props.traderUuid);
// });

const formatDelta = computed(() => {
  if (sum_dinv.value == undefined) {
    return "";
  }
  return sum_dinv.value >= 0 ? "+" + sum_dinv.value : sum_dinv.value;
});

const finalizingDay = () => {
  router.push({ name: "summary", params: { traderUuid: props.traderUuid } });
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

.v-card {
  transition: all 0.3s ease;
  overflow: hidden;
}

.v-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.headline {
  letter-spacing: 0.5px;
}

.v-chip {
  font-weight: 500;
}

.v-navigation-drawer {
  background-color: #f5f5f5;
}

.v-footer {
  transition: all 0.3s ease;
}

.equal-height-columns > .v-col {
  display: flex;
  flex: 1;
}

.flex-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.flex-child {
  flex: 1;
  overflow: auto;
}

@keyframes fadeInHighlight {
  0% {
    background-color: yellow;
    opacity: 0;
  }
  50% {
    background-color: yellow;
    opacity: 0.5;
  }
  100% {
    background-color: transparent;
    opacity: 1;
  }
}

.fade-in-highlight {
  animation: fadeInHighlight 1s ease;
}

.fill-height {
  height: 100%;
}

.v-card {
  display: flex;
  flex-direction: column;
}

.v-card__text {
  flex-grow: 1;
  overflow: hidden;
}

/* Add this new style to ensure consistent spacing */
.v-card__title {
  padding-bottom: 8px;
}

.goal-message {
  background-color: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.goal-success {
  border-left: 4px solid #7CB342;
}

.goal-warning {
  border-left: 4px solid #FFB300;
}

.goal-subtitle {
  color: rgba(255, 255, 255, 0.7) !important;
}

.goal-text {
  color: white !important;
}

.goal-message:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.chart-card {
  background-color: #f5f5f5 !important;
}

.chart-card .v-card__title {
  background-color: #ffffff;
  border-bottom: 1px solid #e0e0e0;
}
</style>