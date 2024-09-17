<template>
  <v-container fluid class="session-summary-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="10" md="8" lg="6">
        <v-card elevation="24" class="session-summary-card">
          <v-card-title class="text-h4 font-weight-bold text-center py-6 primary white--text">
            Trading Session Summary
          </v-card-title>
          <v-card-text class="pa-6">
            <v-row>
              <v-col cols="12" md="6">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Cash Overview</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Initial Cash:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(traderInfo?.initial_cash, 'currency') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">Final Cash:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(traderInfo?.cash, 'currency') }}</span>
                  </div>
                </div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Shares Overview</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Initial Shares:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(traderInfo?.initial_shares, 'number') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">Final Shares:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(traderInfo?.shares, 'number') }}</span>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions class="justify-center pa-6">
            <v-btn color="primary" x-large @click="goToRegister" class="mr-4">
              Return to Login
            </v-btn>
            <v-btn color="secondary" x-large @click="downloadSessionMetrics">
              Download Metrics
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { useRouter } from 'vue-router';
import { useTraderStore } from "@/store/app";

const props = defineProps({
  traderUuid: String,
});

const router = useRouter();
const traderStore = useTraderStore();
const traderInfo = ref(null);
const httpUrl = import.meta.env.VITE_HTTP_URL;

async function fetchTraderInfo() {
  try {
    const response = await axios.get(`${httpUrl}trader_info/${props.traderUuid}`);
    traderInfo.value = response.data.data;
  } catch (error) {
    console.error('Failed to fetch trader info:', error);
  }
}

const formatValue = (value, format) => {
  if (format === 'currency' && typeof value === 'number') {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  } else if (format === 'number' && typeof value === 'number') {
    return value.toLocaleString('en-US');
  }
  return value;
};

const goToRegister = () => {
  traderStore.clearStore(); // Clear the trader store
  router.push({ name: 'Register' });
};

const downloadSessionMetrics = async () => {
  try {
    // Ensure the traderUuid is set in the store
    traderStore.traderUuid = props.traderUuid;
    
    // Call the fetchSessionMetrics action from the store
    await traderStore.fetchSessionMetrics();
  } catch (error) {
    console.error('Failed to download session metrics:', error);
  }
};

onMounted(() => {
  fetchTraderInfo();
  // Ensure the trading session data is set in the store
  if (traderInfo.value && traderInfo.value.trading_session_id) {
    traderStore.tradingSessionData = { trading_session_uuid: traderInfo.value.trading_session_id };
  }
});
</script>

<style scoped>
.session-summary-wrapper {
  background: url('@/assets/trading_background.jpg') no-repeat center center fixed;
  background-size: cover;
  min-height: 100vh;
}

.session-summary-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.session-summary-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
}

.metric-card {
  background-color: rgba(245, 247, 250, 0.8);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
}
</style>