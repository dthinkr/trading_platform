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

      <div class="info-section mt-4">
        <h2>
          <v-icon left :color="iconColor">mdi-progress-check</v-icon>
          Session Progress
        </h2>
        <v-card outlined class="progress-card">
          <v-card-text>
            <div class="d-flex justify-space-between align-center">
              <span class="text-subtitle-1">Current Session:</span>
              <span class="text-h6 font-weight-bold">{{ currentSession }}</span>
            </div>
            <div class="d-flex justify-space-between align-center mt-2">
              <span class="text-subtitle-1">Maximum Sessions:</span>
              <span class="text-h6 font-weight-bold">{{ maxSessionsDisplay }}</span>
            </div>
            <v-progress-linear
              v-if="!isAdmin"
              :value="sessionProgress"
              height="10"
              rounded
              class="mt-4"
              color="primary"
            ></v-progress-linear>
          </v-card-text>
        </v-card>
      </div>

      <!-- <div class="info-section">
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
      </div> -->

      <div class="button-group mt-6">
        <v-btn
          @click="startTrading"
          :loading="isLoading"
          :disabled="!canStartTrading"
          class="start-button mb-2"
        >
          <v-icon left>mdi-play-circle-outline</v-icon>
          {{ startButtonText }}
        </v-btn>

        <v-btn
          @click="handleLogout"
          color="error"
          variant="text"
          class="logout-button"
          :disabled="isLoading"
          size="small"
        >
          <v-icon left small>mdi-logout</v-icon>
          Logout
        </v-btn>
      </div>
    </div>
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
    router.push({ 
      name: 'trading', 
      params: { 
        traderUuid: traderStore.traderUuid,
        sessionId: route.params.sessionId  // Now route is defined
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

const currentSession = computed(() => {
  return props.traderAttributes?.all_attributes?.historical_sessions_count || 1;
});

const maxSessionsPerHuman = computed(() => {
  return props.traderAttributes?.all_attributes?.params?.max_sessions_per_human || 4;
});

const isAdmin = computed(() => {
  return props.traderAttributes?.all_attributes?.is_admin || false;
});

const maxSessionsDisplay = computed(() => {
  if (isAdmin.value) {
    return '∞';
  }
  return maxSessionsPerHuman.value;
});

const sessionProgress = computed(() => {
  if (isAdmin.value) return 100;
  return (currentSession.value / maxSessionsPerHuman.value) * 100;
});
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

.button-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.logout-button {
  width: auto !important;
  height: auto !important;
  font-size: 0.875rem !important;
  font-weight: 400 !important;
  text-transform: none;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  margin: 0 auto;
}

.logout-button:hover {
  box-shadow: none !important;
  opacity: 0.8;
}

.progress-card {
  background-color: rgba(245, 247, 250, 0.8);
  transition: all 0.3s ease;
}

.progress-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
}
</style>
