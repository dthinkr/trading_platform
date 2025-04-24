<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="10" md="8" lg="6">
        <v-card elevation="24" class="market-summary-card">
          <v-card-title class="text-h4 font-weight-bold text-center py-6 primary white--text">
            Trading Market Summary
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
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Initial_Midprice, 'number') }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Final Midpice:</span>
                    <span class="text-h6 font-weight-bold">{{ formatValue(orderBookMetrics?.Last_Midprice, 'number') }}</span>
                  </div>
                  <div v-if="traderSpecificMetrics" class="mt-3">
                    <h4 class="text-subtitle-1 font-weight-medium mb-2">Your Trading Activity</h4>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Your Trades:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Trades, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Your VWAP:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.VWAP, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Remaining Trades:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Remaining_Trades, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Penalized VWAP:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Penalized_VWAP, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Slippage:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Slippage, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Slippage Scaled:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Slippage_Scaled, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">PnL:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.PnL, 'number') }}</span>
                    </div>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="text-subtitle-1">Market Reward:</span>
                      <span class="text-h6 font-weight-bold">{{ formatValue(traderSpecificMetrics.Reward, 'gbp') }}</span>
                    </div>
                  </div>
                </div>
              </v-col>
              <v-col cols="12">
                <div class="metric-card pa-4 mb-4">
                  <h3 class="text-h6 font-weight-medium mb-2">Market Progress</h3>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-subtitle-1">Current Market:</span>
                    <span class="text-h6 font-weight-bold">{{ currentMarket }}</span>
                  </div>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-subtitle-1">Maximum Markets:</span>
                    <span class="text-h6 font-weight-bold">{{ maxMarketsDisplay }}</span>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions class="justify-center pa-6">
            <template v-if="isLastMarket">
              <div class="text-center">
                <h2 class="text-h5 mb-4 primary--text">Thank you for your participation!</h2>
                <p class="text-subtitle-1 mb-4">
                  You have completed all trading markets.<br>
                  Your market reward is {{formatValue(traderSpecificMetrics?.Accumulated_Reward, 'gbp') }}. Your participation fee is {{formatValue(5, 'gbp')}}.
                  <br></br>
                  Your final payment will be {{formatValue(traderSpecificMetrics?.Accumulated_Reward + 5, 'gbp') }}.
                </p>
                
                <!-- Questionnaire Section -->
                <div v-if="!questionnaireCompleted" class="questionnaire-section mt-4 mb-4">
                  <h3 class="text-h6 mb-3">Please complete this short questionnaire before finishing</h3>
                  
                  <!-- Question 1 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">1. How would you rate your overall experience with the trading platform?</p>
                    <v-radio-group v-model="questionnaire.q1" row>
                      <v-radio label="Poor" value="Poor"></v-radio>
                      <v-radio label="Fair" value="Fair"></v-radio>
                      <v-radio label="Good" value="Good"></v-radio>
                      <v-radio label="Very Good" value="Very Good"></v-radio>
                      <v-radio label="Excellent" value="Excellent"></v-radio>
                    </v-radio-group>
                  </div>
                  
                  <!-- Question 2 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">2. How easy was it to understand the trading interface?</p>
                    <v-radio-group v-model="questionnaire.q2" row>
                      <v-radio label="Very Difficult" value="Very Difficult"></v-radio>
                      <v-radio label="Difficult" value="Difficult"></v-radio>
                      <v-radio label="Neutral" value="Neutral"></v-radio>
                      <v-radio label="Easy" value="Easy"></v-radio>
                      <v-radio label="Very Easy" value="Very Easy"></v-radio>
                    </v-radio-group>
                  </div>
                  
                  <!-- Question 3 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">3. Did you feel that your trading strategy improved over time?</p>
                    <v-radio-group v-model="questionnaire.q3" row>
                      <v-radio label="Not at all" value="Not at all"></v-radio>
                      <v-radio label="Slightly" value="Slightly"></v-radio>
                      <v-radio label="Moderately" value="Moderately"></v-radio>
                      <v-radio label="Considerably" value="Considerably"></v-radio>
                      <v-radio label="Significantly" value="Significantly"></v-radio>
                    </v-radio-group>
                  </div>
                  
                  <!-- Question 4 -->
                  <div class="question-container mb-4">
                    <p class="text-subtitle-1 mb-2">4. Would you participate in similar trading experiments in the future?</p>
                    <v-radio-group v-model="questionnaire.q4" row>
                      <v-radio label="Definitely not" value="Definitely not"></v-radio>
                      <v-radio label="Probably not" value="Probably not"></v-radio>
                      <v-radio label="Maybe" value="Maybe"></v-radio>
                      <v-radio label="Probably yes" value="Probably yes"></v-radio>
                      <v-radio label="Definitely yes" value="Definitely yes"></v-radio>
                    </v-radio-group>
                  </div>
                  
                  <v-btn 
                    color="primary" 
                    x-large 
                    @click="submitQuestionnaire"
                    :disabled="!isQuestionnaireComplete"
                    class="mt-2"
                  >
                    Submit Questionnaire
                  </v-btn>
                </div>
                
                <!-- Show this after questionnaire is completed -->
                <div v-if="questionnaireCompleted" class="mt-4">
                  <p class="text-subtitle-1 mb-4">
                    <span class="font-weight-bold">Please click <a :href="prolificRedirectUrl" target="_blank" class="primary--text">here</a> to complete your submission on Prolific.</span>
                  </p>
                  <v-btn 
                    color="secondary" 
                    x-large 
                    @click="downloadMarketMetrics"
                    class="mt-2"
                  >
                    Download Metrics
                  </v-btn>
                </div>
              </div>
            </template>
            <template v-else>
              <v-btn
                color="primary" 
                x-large 
                @click="goToRegister" 
                class="mr-4"
              >
                Continue to Next Market
              </v-btn>
              <v-btn 
                color="secondary" 
                x-large 
                @click="downloadMarketMetrics"
              >
                Download Metrics
              </v-btn>
            </template>
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
import { useAuthStore } from "@/store/auth";
import { storeToRefs } from "pinia";

const props = defineProps({
  traderUuid: String,
});

const router = useRouter();
const traderStore = useTraderStore();
const authStore = useAuthStore();
const { pnl, vwap } = storeToRefs(traderStore);
const traderInfo = ref(null);
const orderBookMetrics = ref(null);
const traderSpecificMetrics = ref(null);
const httpUrl = import.meta.env.VITE_HTTP_URL;
const prolificRedirectUrl = import.meta.env.VITE_PROLIFIC_REDIRECT_URL || 'https://app.prolific.com/submissions/complete?cc=C11I8OGE';
const showDialog = ref(false);
const dialogTitle = ref('');
const dialogMessage = ref('');

// Questionnaire state
const questionnaireCompleted = ref(false);
const questionnaire = ref({
  q1: null,
  q2: null,
  q3: null,
  q4: null
});

// Check if all questions are answered
const isQuestionnaireComplete = computed(() => {
  return questionnaire.value.q1 && 
         questionnaire.value.q2 && 
         questionnaire.value.q3 && 
         questionnaire.value.q4;
});

// Submit questionnaire responses
async function submitQuestionnaire() {
  try {
    // Prepare responses array
    const responses = [
      questionnaire.value.q1,
      questionnaire.value.q2,
      questionnaire.value.q3,
      questionnaire.value.q4
    ];
    
    // Send to backend
    const response = await axios.post(`${httpUrl}save_questionnaire_response`, {
      trader_id: props.traderUuid,
      responses: responses
    });
    
    if (response.data.status === 'success') {
      questionnaireCompleted.value = true;
      // Success case - no dialog shown, just proceed to show the redirect URL
    } else {
      dialogTitle.value = 'Error';
      dialogMessage.value = 'There was an error saving your responses. Please try again.';
      showDialog.value = true;
    }
  } catch (error) {
    console.error('Error submitting questionnaire:', error);
    dialogTitle.value = 'Error';
    dialogMessage.value = 'There was an error saving your responses. Please try again.';
    showDialog.value = true;
  }
};

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
  } else if (format === 'gbp' && typeof value === 'number') {
    return value.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });
  } else if (format === 'number' && typeof value === 'number') {
    return value.toLocaleString('en-US');
  }
  return value;
};

const goToRegister = () => {
  // Check if the user is a Prolific user
  if (authStore.user?.isProlific) {
    console.log('Prolific user detected, preparing for next market');
    
    // Mark this user as having completed onboarding
    if (authStore.user?.uid) {
      localStorage.setItem(`prolific_onboarded_${authStore.user.uid}`, 'true');
      authStore.prolificUserHasCompletedOnboarding = true;
      
      // Store a flag indicating this is a continuation to the next market
      // This will help prevent immediate redirection to the market summary
      localStorage.setItem('prolific_next_market', 'true');
      
      // Store Prolific parameters in localStorage for auto-login
      if (authStore.user.prolificData) {
        const prolificData = {
          PROLIFIC_PID: authStore.user.prolificData.PROLIFIC_PID,
          STUDY_ID: authStore.user.prolificData.STUDY_ID,
          SESSION_ID: authStore.user.prolificData.SESSION_ID,
          timestamp: Date.now()
        };
        
        console.log('Storing Prolific data for auto-login:', prolificData);
        localStorage.setItem('prolific_auto_login', JSON.stringify(prolificData));
      }
    }
  }
  
  // Use the original behavior - redirect to register which will trigger the root page reload
  console.log('Redirecting to register page (original behavior)');
  router.push({ name: 'Register', replace: true }).then(() => {
    window.location.href = '/register';
  });
};

const currentMarket = computed(() => {
  return traderInfo.value?.all_attributes?.historical_markets_count || 1;
});

const maxMarketsDisplay = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin) {
    return '∞';
  }
  return traderInfo.value?.all_attributes?.params?.max_markets_per_human || 'Loading...';
});

const isLastMarket = computed(() => {
  if (traderInfo.value?.all_attributes?.is_admin) return false;
  const currentCount = traderInfo.value?.all_attributes?.historical_markets_count || 1;
  const maxMarkets = traderInfo.value?.all_attributes?.params?.max_markets_per_human || 4;
  return currentCount >= maxMarkets;
});

onMounted(() => {
  fetchTraderInfo();
  // Ensure the trading market data is set in the store
  if (traderInfo.value && traderInfo.value.trading_market_id) {
    traderStore.tradingMarketData = { trading_market_uuid: traderInfo.value.trading_market_id };
  }
});
</script>

<style scoped>
.market-summary-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
  max-width: 800px;
  width: 100%;
}

.market-summary-card:hover {
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

.questionnaire-section {
  background-color: rgba(245, 247, 250, 0.9);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
}

.question-container {
  text-align: left;
  background-color: rgba(255, 255, 255, 0.7);
  padding: 15px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.question-container:hover {
  background-color: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
</style>
