<template>
  <div class="card-content">
    <v-card class="mb-6" elevation="3" shaped color="primary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-clock-outline</v-icon>
        Duration
      </v-card-title>
      <v-card-text class="text-h5">
        <p>Now you will practice using the trading platform for <span class="font-weight-bold">5 minutes</span>.</p>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-table</v-icon>
        Your Trading Parameters
      </v-card-title>
      <v-card-text>
        <v-table class="parameters-table">
          <thead>
            <tr>
              <th class="text-left text-h6">Parameter</th>
              <th class="text-left text-h6">Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="text-subtitle-1">Goal</td>
              <td class="text-subtitle-1">{{ goalDescription }}</td>
            </tr>
            <tr>
              <td class="text-subtitle-1">Initial Shares</td>
              <td class="text-subtitle-1">{{ initialShares }}</td>
            </tr>
            <tr>
              <td class="text-subtitle-1">Initial Cash</td>
              <td class="text-subtitle-1">{{ initialCash }} Liras</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-information-outline</v-icon>
        Important Rules
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined class="h-100">
              <v-card-title class="text-h6 font-weight-medium">
                <v-icon left color="warning">mdi-timer-sand</v-icon>
                Cancellation Policy
              </v-card-title>
              <v-card-text class="text-body-1">
                When you place a passive order (bid or ask) you cannot cancel it for {{ cancelTime }} seconds. 
                After {{ cancelTime }} seconds have passed you can cancel it (if you want).
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card outlined class="h-100">
              <v-card-title class="text-h6 font-weight-medium">
                <v-icon left color="info">mdi-file-document-multiple-outline</v-icon>
                Order Quantity
              </v-card-title>
              <v-card-text class="text-body-1">
                Each order is for one share only and you can choose the price. 
                If you want to place an order for a quantity of X shares at price P, you need to place X orders at price P.
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card class="mb-6 start-trading-btn" elevation="3" shaped color="success" dark @click="startPractice">
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-play-circle-outline</v-icon>
        Ready to Start
      </v-card-title>
      <v-card-text class="text-h5">
        <p>You're now ready to begin your practice session. Good luck!</p>
      </v-card-text>
    </v-card>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const traderStore = useTraderStore();
const { gameParams, tradingSessionData } = storeToRefs(traderStore);

const cancelTime = computed(() => gameParams.value?.cancel_time || 'Loading...');

const currentTraderData = computed(() => {
  const traderUuid = route.params.traderUuid;
  const trader = tradingSessionData.value?.human_traders?.find(trader => trader.id === traderUuid) || {};
  console.log('Current Trader Data:', trader);
  return trader;
});

const goalDescription = computed(() => {
  const goal = currentTraderData.value?.goal;
  if (goal === undefined || goal === null) return 'Loading...';
  if (goal === 0) return 'No specific goal';
  return goal < 0 ? `Sell ${Math.abs(goal)} shares` : `Buy ${goal} shares`;
});

const initialShares = computed(() => {
  const goal = currentTraderData.value?.goal;
  if (goal === undefined || goal === null) return 'Loading...';
  // If the goal is to sell, assume the initial shares are equal to the absolute value of the goal
  if (goal < 0) return Math.abs(goal);
  // If the goal is to buy or no goal, assume initial shares are 0
  return 0;
});

const initialCash = computed(() => currentTraderData.value?.initial_cash ?? 'Loading...');

const startPractice = () => {
  router.push({ name: 'trading', params: { traderUuid: route.params.traderUuid } });
};

onMounted(async () => {
  console.log('Component mounted. tradingSessionData:', tradingSessionData.value);
  console.log('Route params:', route.params);
  if (!tradingSessionData.value?.trading_session_uuid) {
    await traderStore.getTradingSessionData(route.params.traderUuid);
    console.log('After fetching data. tradingSessionData:', tradingSessionData.value);
  }
});

watch(tradingSessionData, (newValue) => {
  console.log('tradingSessionData changed:', newValue);
}, { deep: true });

watch(gameParams, (newValue) => {
  console.log('gameParams changed:', newValue);
}, { deep: true });
</script>

<style scoped>
.card-content {
  max-width: 800px;
  margin: 0 auto;
}

.parameters-table {
  width: 100%;
  border-collapse: collapse;
}

.parameters-table th,
.parameters-table td {
  border: 1px solid rgba(0, 0, 0, 0.12);
  padding: 12px;
}

.parameters-table th {
  background-color: rgba(0, 0, 0, 0.03);
}

.start-trading-btn {
  cursor: pointer;
  transition: transform 0.2s;
}

.start-trading-btn:hover {
  transform: scale(1.02);
}

.h-100 {
  height: 100%;
}

.v-card-text {
  height: 100%;
  overflow-y: auto;
}
</style>