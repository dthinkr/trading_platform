<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-rocket-launch</v-icon>
        <h2 class="text-h4 gradient-text">Ready to Trade</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Duration Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-clock-outline</v-icon>
                  <span class="text-h6">Duration</span>
                </div>
                <p class="text-body-1">
                  Trade for <span class="highlight-text">{{ marketDuration }} minutes</span>
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Progress Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-progress-check</v-icon>
                  <span class="text-h6">Market Progress</span>
                </div>
                <div class="d-flex justify-space-between align-center mb-2">
                  <span>Markets You Have Played:</span>
                  <span class="highlight-text">{{ currentMarket }}</span>
                </div>
                <div class="d-flex justify-space-between align-center mb-3">
                  <span>Markets You Can Still Play:</span>
                  <span class="highlight-text">{{ remainingMarkets }}</span>
                </div>
                <v-progress-linear
                  v-if="!isAdmin"
                  :value="marketProgress"
                  height="8"
                  rounded
                  striped
                  color="primary"
                ></v-progress-linear>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Parameters Table Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-table</v-icon>
                  <span class="text-h6">Trading Parameters</span>
                </div>
                <v-data-table
                  :headers="headers"
                  :items="items"
                  hide-default-footer
                  disable-pagination
                  class="parameters-table"
                ></v-data-table>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>

      <!-- Action Buttons -->
      <div class="action-buttons mt-6">
        <v-btn
          @click="startTrading"
          :loading="isLoading"
          :disabled="!canStartTrading"
          class="start-button"
          size="x-large"
          elevation="2"
        >
          <v-icon left class="mr-2">mdi-play-circle-outline</v-icon>
          {{ startButtonText }}
        </v-btn>

        <v-btn
          @click="handleLogout"
          color="error"
          variant="text"
          class="logout-button mt-2"
          :disabled="isLoading"
        >
          <v-icon left class="mr-1">mdi-logout</v-icon>
          Logout
        </v-btn>
      </div>
    </v-container>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from "@/store/auth";
import { auth } from "@/firebaseConfig";

const router = useRouter();
const route = useRoute();

const traderStore = useTraderStore();
const { goalMessage } = storeToRefs(traderStore);

const props = defineProps({
  traderAttributes: Object,
  iconColor: String
});

const isLoading = ref(false);

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 'Loading...';
});
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
    await traderStore.startTradingMarket();
    router.push({ 
      name: 'trading', 
      params: { 
        traderUuid: traderStore.traderUuid,
        marketId: route.params.marketId  // Now route is defined
      } 
    });
  } catch (error) {
    console.error('Failed to initialize trading system:', error);
  } finally {
    isLoading.value = false;
  }
};

const authStore = useAuthStore();

const handleLogout = async () => {
  try {
    // Sign out from Firebase
    await auth.signOut();
    // Clear auth store state
    authStore.logout();
    // Clear trader store state
    traderStore.$reset();
    // Redirect to registration page
    router.push('/');
  } catch (error) {
    console.error('Logout failed:', error);
  }
};

const currentMarket = computed(() => {
  return props.traderAttributes?.all_attributes?.historical_markets_count || 0;
});

const maxMarketsPerHuman = computed(() => {
  return props.traderAttributes?.all_attributes?.params?.max_markets_per_human || 4;
});

const isAdmin = computed(() => {
  return props.traderAttributes?.all_attributes?.is_admin || false;
});

const remainingMarkets = computed(() => {
  if (isAdmin.value) return '∞';
  return maxMarketsPerHuman.value - currentMarket.value;
});

const marketProgress = computed(() => {
  if (isAdmin.value) return 100;
  return (currentMarket.value / maxMarketsPerHuman.value) * 100;
});
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header-section {
  text-align: center;
  margin-bottom: 3rem;
}

.gradient-text {
  background: linear-gradient(45deg, #2196F3, #4CAF50);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
  margin: 1rem 0;
}

.pulse-icon {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.info-card {
  height: 100%;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.highlight-text {
  color: #1976D2;
  font-weight: 600;
  font-size: 1.1rem;
}

.parameters-table {
  border-radius: 8px;
  overflow: hidden;
}

.start-button {
  width: 100%;
  max-width: 400px;
  height: 56px;
  font-size: 1.1rem;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  background: linear-gradient(45deg, #2196F3, #4CAF50) !important;
  color: white !important;
  transition: all 0.3s ease;
}

.start-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
}

.action-buttons {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 2rem;
}

.logout-button {
  font-size: 0.9rem;
  text-transform: none;
}

@media (max-width: 960px) {
  .page-container {
    padding: 1rem;
  }
}
</style>
