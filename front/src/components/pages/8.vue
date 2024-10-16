<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-clock-outline</v-icon>
          Duration
        </h2>
        <p>Now you will practice using the trading platform for <span class="dynamic-value">5 minutes</span>.</p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-table</v-icon>
          Your Trading Parameters
        </h2>
        <v-data-table
          :headers="headers"
          :items="items"
          hide-default-footer
          disable-pagination
          class="elevation-1"
        ></v-data-table>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-information-outline</v-icon>
          Important Rules
        </h2>
        <v-row>
          <v-col cols="12" md="6">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="warning">mdi-timer-sand</v-icon>
                Cancellation Policy
              </v-card-title>
              <v-card-text>
                When you place a passive order (bid or ask) you cannot cancel it for {{ cancelTime }} seconds. 
                After {{ cancelTime }} seconds have passed you can cancel it (if you want).
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card outlined>
              <v-card-title>
                <v-icon left color="info">mdi-file-document-multiple-outline</v-icon>
                Order Quantity
              </v-card-title>
              <v-card-text>
                Each order is for one share only and you can choose the price. 
                If you want to place an order for a quantity of X shares at price P, you need to place X orders at price P.
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </div>

      <v-btn
        @click="startTrading"
        :loading="isLoading"
        :disabled="!canStartTrading"
        class="start-button mt-6"
      >
        <v-icon left>mdi-play-circle-outline</v-icon>
        {{ startButtonText }}
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter } from 'vue-router';

const router = useRouter();
const traderStore = useTraderStore();
const { goalMessage } = storeToRefs(traderStore);

const props = defineProps({
  traderAttributes: Object,
  iconColor: String
});

const isLoading = ref(false);

const cancelTime = computed(() => props.traderAttributes?.all_attributes?.params?.cancel_time || 'Loading...');
const goalDescription = computed(() => {
  if (!goalMessage.value) return 'You can freely trade in this market. Your goal is to make a profit.';
  return goalMessage.value.text;
});
const initialShares = computed(() => props.traderAttributes?.shares ?? 'Loading...');
const initialCash = computed(() => props.traderAttributes?.cash ?? 'Loading...');
const canStartTrading = computed(() => !!props.traderAttributes?.all_attributes?.params);
const startButtonText = computed(() => isLoading.value ? 'Starting...' : 'Start Trading');

const headers = [
  { text: 'Parameter', value: 'parameter', align: 'left' },
  { text: 'Value', value: 'value', align: 'left' },
];

const items = computed(() => {
  const baseItems = [
    { parameter: 'Goal', value: goalDescription.value },
    { parameter: 'Initial Shares', value: initialShares.value },
    { parameter: 'Initial Cash', value: initialCash.value ? `${initialCash.value} Liras` : 'Loading...' },
  ];

  // If the goal is free trading, we don't need to show additional parameters
  if (goalDescription.value.toLowerCase().includes('freely trade')) {
    return baseItems;
  }

  // For buying or selling goals, add more specific information
  const goalValue = props.traderAttributes?.goal;
  if (goalValue !== undefined && goalValue !== null) {
    if (goalValue > 0) {
      baseItems.push({ parameter: 'Shares to Buy', value: goalValue });
    } else if (goalValue < 0) {
      baseItems.push({ parameter: 'Shares to Sell', value: Math.abs(goalValue) });
    }
  }

  return baseItems;
});

const startTrading = async () => {
  if (!canStartTrading.value) {
    console.error('Cannot start trading: parameters are not available');
    return;
  }

  isLoading.value = true;
  try {
    await traderStore.initializeTradingSystemWithPersistentSettings();
    await traderStore.getTraderAttributes(traderStore.traderUuid);
    await traderStore.startTradingSession();
    router.push({ name: 'trading', params: { traderUuid: traderStore.traderUuid } });
  } catch (error) {
    console.error('Failed to initialize trading system:', error);
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.start-button {
  width: 100%;
  height: 3.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  background-color: #4caf50 !important;
  color: white !important;
  transition: all 0.3s ease;
}

.start-button:hover {
  background-color: #45a049 !important;
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}
</style>
