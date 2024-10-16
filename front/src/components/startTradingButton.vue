<template>
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
    {{ buttonText }}
  </v-btn>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useTraderStore } from "@/store/app";

const props = defineProps({
  buttonText: {
    type: String,
    default: 'Start Trading'
  }
});

const router = useRouter();
const traderStore = useTraderStore();

const isLoading = ref(false);

const canStartTrading = computed(() => {
  return !!traderStore.traderAttributes?.all_attributes?.params;
});

const startTrading = async () => {
  if (!canStartTrading.value) {
    console.error('Cannot start trading: parameters are not available');
    return;
  }

  isLoading.value = true;
  try {
    await traderStore.startTradingSession();
    
    // Navigate to the trading page
    router.push({ 
      name: 'trading', 
      params: { 
        traderUuid: traderStore.traderUuid,
        sessionId: traderStore.tradingSessionData.trading_session_uuid 
      } 
    });
  } catch (error) {
    console.error('Failed to start trading:', error);
    // You might want to show an error message to the user here
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.start-trading-btn {
  transition: transform 0.2s;
}

.start-trading-btn:hover {
  transform: scale(1.02);
}
</style>
