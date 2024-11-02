<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="10" md="8" lg="6">
        <v-card elevation="24" class="session-summary-card">
          <v-card-title class="text-h4 font-weight-bold text-center py-6 primary white--text">
            Trading Session Summary
          </v-card-title>
          <v-card-text class="pa-6">
            <v-row>
              <!-- <v-col cols="12" md="6">
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
              </v-col> -->
              <!-- <v-col cols="12" md="6">
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
              </v-col> -->
              <!-- <v-col cols="12">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Performance Metrics</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">PNL:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(pnl, 'currency') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">VWAP:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(vwap, 'currency') }}</span>
                  </div>
                </div>
              </v-col> -->
              <!-- New content: Order Book Metrics -->
              <v-col cols="12">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Order Book Metrics</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Total Orders:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Total_Orders, 'number') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Total Trades:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Total_Trades, 'number') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Total Cancellations:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Total_Cancellations, 'number') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Initial Midpice:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Initial_Midprice, 'currency') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Final Midpice:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Last_Midprice, 'currency') }}</span>
                  </div>
                  <div v-if="traderSpecificMetrics" class="mt-3">
                    <h4 class="text-subtitle-1 font-weight-medium mb-2">Your Trading Activity</h4>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Your Trades:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Trades, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Your VWAP:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.VWAP, 'currency') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Remaining Trades:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Remaining_Trades, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Penalized VWAP:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Penalized_VWAP, 'currency') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Slippage:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Slippage, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">PnL:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.PnL, 'currency') }}</span>
                    </div>
                  </div>
                </div>
              </v-col>
              <v-col cols="12">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Session Progress</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Current Session:</span>
                    <span class="text-h6 font-weight-bold">{{ currentSession }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">Maximum Sessions:</span>
                    <span class="text-h6 font-weight-bold">{{ maxSessionsDisplay }}</span>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions class="justify-center pa-6">
            <v-btn
              color="primary" 
              x-large 
              @click="goToRegister" 
              class="mr-4"
            >
              {{ canContinue ? 'Continue to Next Session' : 'End of Sessions' }}
            </v-btn>
            <v-btn 
              color="secondary" 
              x-large 
              @click="downloadSessionMetrics"
            >
              Download Metrics
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
  <v-dialog v-model="showDialog" max-width="400">
    <v-card>
      <v-card-title class="headline">{{ dialogTitle }}</v-card-title>
      <v-card-text>{{ dialogMessage }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="closeDialog">OK</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import axios from "axios";
import { useRouter } from 'vue-router';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const props = defineProps({
  traderUuid: String,
});

const router = useRouter();
const traderStore = useTraderStore();
const { pnl, vwap } = storeToRefs(traderStore);
const traderInfo = ref(null);
const orderBookMetrics = ref(null);
const traderSpecificMetrics = ref(null);
const httpUrl = import.meta.env.VITE_HTTP_URL;
const showDialog = ref(false);
const dialogTitle = ref('');
const dialogMessage = ref('');

const maxRetries = 3;
const retryDelay = 1000; // 1 second

async function fetchTraderInfo() {
  try {
    const response = await axios.get(`${httpUrl}trader_info/${props.traderUuid}`);
    traderInfo.value = response.data.data;
    orderBookMetrics.value = response.data.data.order_book_metrics;
    traderSpecificMetrics.value = response.data.data.trader_specific_metrics;

    // If metrics are missing, retry just for metrics
    if (traderInfo.value && (!orderBookMetrics.value || !traderSpecificMetrics.value)) {
      let retryCount = 0;
      const retryMetrics = async () => {
        if (retryCount >= maxRetries) return;
        
        console.log(`Retrying metrics fetch attempt ${retryCount + 1}`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        
        try {
          const retryResponse = await axios.get(`${httpUrl}trader_info/${props.traderUuid}`);
          if (retryResponse.data.data) {
            orderBookMetrics.value = retryResponse.data.data.order_book_metrics;
            traderSpecificMetrics.value = retryResponse.data.data.trader_specific_metrics;
            
            if (orderBookMetrics.value && traderSpecificMetrics.value) {
              console.log('Successfully loaded metrics on retry');
              return;
            }
          }
          retryCount++;
          await retryMetrics();
        } catch (error) {
          console.error('Error in metrics retry:', error);
          retryCount++;
          await retryMetrics();
        }
      };
      
      retryMetrics();
    }
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
  router.push({ name: 'Register', replace: true }).then(() => {
    window.location.href = '/register';
  });
};

const canContinue = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin) return true;
  const currentCount = traderInfo.value?.all_attributes?.historical_sessions_count || 1;
  const maxSessions = traderInfo.value?.all_attributes?.params?.max_sessions_per_human || 4;
  return currentCount < maxSessions;
});

const currentSession = computed(() => {
  return traderInfo.value?.all_attributes?.historical_sessions_count || 1;
});

const maxSessionsDisplay = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin) {
    return '∞';
  }
  return traderInfo.value?.all_attributes?.params?.max_sessions_per_human || 'Loading...';
});

onMounted(() => {
  fetchTraderInfo();
  // Ensure the trading session data is set in the store
  if (traderInfo.value && traderInfo.value.trading_session_id) {
    traderStore.tradingSessionData = { trading_session_uuid: traderInfo.value.trading_session_id };
  }
});
</script>

<style scoped>
.session-summary-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
  max-width: 800px;
  width: 100%;
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
