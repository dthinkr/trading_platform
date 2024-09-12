<template>
  <v-app class="trading-system">
    <v-app-bar app elevation="2" color="primary" dark>
      <v-container class="py-0 fill-height">
        <v-row align="center" no-gutters>
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
        </v-row>
      </v-container>
    </v-app-bar>

    <v-main class="grey lighten-4">
      <v-container fluid class="pa-6">
        <v-row>
          <v-col cols="12" lg="6">
            <v-card class="mb-6" elevation="3">
              <v-card-text class="pa-0">
                <BidAskDistribution />
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" lg="6">
            <v-card class="mb-6" elevation="3">
              <v-card-text class="pa-0">
                <PriceHistory />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12" lg="6">
            <ActiveOrders />
          </v-col>
          <v-col cols="12" lg="6">
            <OrderPanel />
          </v-col>
        </v-row>
      </v-container>
    </v-main>
    <v-navigation-drawer app right width="350" permanent class="elevation-4">
      <v-container fluid class="pa-4">
        <OrderHistory class="mb-6" />
        <MarketIndicators />
      </v-container>
    </v-navigation-drawer>

    <v-footer app v-if="goalMessage" :color="goalMessage.type" class="px-4" elevation="3">
      <v-row no-gutters align="center" justify="center">
        <strong class="text-h6">{{ goalMessage.text }}</strong>
      </v-row>
    </v-footer>
  </v-app>
</template>

<script setup>
const props = defineProps({
  traderUuid: String,
});

// Updated imports
import BidAskDistribution from "@charts/BidAskDistribution.vue";
import PriceHistory from "@charts/PriceHistory.vue";
import OrderPanel from "@trading/OrderPanel.vue";
import OrderHistory from "@trading/OrderHistory.vue";
import ActiveOrders from "@trading/ActiveOrders.vue";
import MarketIndicators from "@trading/MarketIndicators.vue";

import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useFormatNumber } from "@/composables/utils";

const { formatNumber } = useFormatNumber();
const router = useRouter();
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";
import { watch } from "vue";
const { initializeTrader } = useTraderStore();
const { gameParams, goalMessage, shares, cash, sum_dinv, initial_shares, dayOver, pnl, vwap, remainingTime, isTradingStarted } =
  storeToRefs(useTraderStore());

onMounted(() => {
  initializeTrader(props.traderUuid);
});

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
  gameParams,
  (newValue) => {
    if (newValue && newValue.active === false && isTradingStarted.value) {
      finalizingDay();
    }
  },
  { deep: true }
);

watch(
  dayOver,
  (newValue) => {
    if (newValue && isTradingStarted.value) {
      finalizingDay();
    }
  }
);

watch(
  remainingTime,
  (newValue) => {
    if (newValue !== null && newValue <= 0 && isTradingStarted.value) {
      finalizingDay();
    }
  }
);

watch(
  remainingTime,
  (newValue) => {
    if (newValue !== null && newValue <= 0) {
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
</style>