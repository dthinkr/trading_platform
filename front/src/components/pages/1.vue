<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          Financial Market Study
        </h2>
        <p>In this study, we investigate decision-making in financial markets. The following are the instructions for this study. Please follow them carefully.</p>
      </div>

      <div class="highlight-box success">
        <v-icon color="green darken-1">mdi-cash-multiple</v-icon>
        <p>You can earn considerable money depending on your decisions, which we will transfer to your bank account the next working day.</p>
      </div>

      <div class="info-section">
        <h2>Study Overview</h2>
        <p>You will participate in markets where you can earn money by trading with other participants on our trading platform. Each market will last <span class="dynamic-value">{{ marketDuration }} minutes</span> and you will participate in <span class="dynamic-value">{{ numMarkets }} markets</span>.</p>
      </div>

      <div class="info-section">
        <h2>After each market:</h2>
        <ul>
          <li>All your remaining shares and money are converted to pounds sterling</li>
          <li>You earn this amount from that market</li>
          <li>A new market starts</li>
          <li>You cannot use your earnings from the previous market to trade in the following markets</li>
        </ul>
      </div>

      <div class="highlight-box info">
        <v-icon color="blue darken-1">mdi-information-outline</v-icon>
        <p>In the following pages, you will learn more about the trading platform and how to trade.</p>
      </div>
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
  return isLoading.value ? 'Starting...' : 'Start Trading';
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