<template>
  <div class="card-content">
    <v-btn
      color="success"
      x-large
      block
      @click="startTrading"
      class="start-trading-btn text-h5 mb-6"
      :loading="isLoading"
      :disabled="!canStartTrading"
    >
      <v-icon left>mdi-play-circle-outline</v-icon>
      {{ startButtonText }}
    </v-btn>

    <p class="text-h5 mb-4">
      In this study, we investigate decision-making in financial markets. The following are the instructions for this study. Please follow them carefully.
    </p>
    <v-alert
      color="success"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-cash"
      class="mb-4 text-h5"
    >
      You can earn considerable money depending on your decisions, which we will transfer to your bank account the next working day.
    </v-alert>
    <p class="text-h5 mb-4">
      You will participate in markets where you can earn money by trading with other participants on our trading platform. Each market will last <span class="dynamic-value">{{ marketDuration }} minutes</span> and you will participate in <span class="dynamic-value">{{ numMarkets }} markets</span>.
    </p>
    <v-divider class="my-4"></v-divider>
    <p class="text-h5 mb-4">
      After each market:
    </p>
    <ul class="mb-4 text-h5 custom-list">
      <li>All your remaining shares and money are converted to pounds sterling</li>
      <li>You earn this amount from that market</li>
      <li>A new market starts</li>
      <li>You cannot use your earnings from the previous market to trade in the following markets</li>
    </ul>
    <v-alert
      color="info"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-information"
      class="mt-4 text-h5 mb-6"
    >
      In the following pages, you will learn more about the trading platform and how to trade.
    </v-alert>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { useTraderStore } from "@/store/app";
import { computed, ref } from 'vue';

const router = useRouter();
const traderStore = useTraderStore();

const isLoading = ref(false);

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0;
});

const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.num_rounds || 0;
});

const canStartTrading = computed(() => {
  return !!traderStore.traderAttributes?.all_attributes?.params;
});

const startButtonText = computed(() => {
  return isLoading.value ? 'Starting...' : 'Start Trading (For Testing Only)';
});

const startTrading = async () => {
  if (!canStartTrading.value) {
    console.error('Cannot start trading: parameters are not available');
    return;
  }

  isLoading.value = true;
  try {
    // Initialize the trading system with parameters from traderAttributes
    await traderStore.initializeTradingSystem(traderStore.traderAttributes.all_attributes.params);
    
    // Navigate to the trading page
    router.push({ name: 'trading', params: { traderUuid: traderStore.traderUuid } });
  } catch (error) {
    console.error('Failed to initialize trading system:', error);
    // You might want to show an error message to the user here
  } finally {
    isLoading.value = false;
  }
};

</script>

<style scoped>
.custom-list {
  padding-left: 1.5em;
  list-style-position: outside;
}

.custom-list li {
  margin-bottom: 0.5em;
}

.start-trading-btn {
  transition: transform 0.2s;
}

.start-trading-btn:hover {
  transform: scale(1.02);
}

.dynamic-value {
  display: inline-block;
  padding: 2px 6px;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  color: #1976D2;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.dynamic-value:hover {
  background-color: rgba(0, 0, 0, 0.1);
}
</style>