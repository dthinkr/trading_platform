<template>
  <v-container fluid class="fill-height pa-0">
    <v-row justify="center" align="center" class="fill-height">
      <v-col cols="12" md="10" lg="8">
        <v-card class="elevation-4">
          <v-card-text>
            <v-container class="pa-0">
              <v-row no-gutters>
                <v-col cols="12">
                  <div class="info-section mb-6">
                    <h2 class="text-h4 font-weight-bold primary--text">
                      <v-icon left color="light-blue" large>{{ pageIcons[currentPageIndex] }}</v-icon>
                      {{ pageTitles[currentPageIndex] }}
                    </h2>
                  </div>
                </v-col>
                <v-col cols="12">
                  <component 
                    :is="pageComponents[currentPageIndex]" 
                    :traderAttributes="traderAttributes"
                    :iconColor="deepBlueColor"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions>
            <v-btn @click="prevPage" :disabled="currentPageIndex === 0">Previous</v-btn>
            <v-spacer></v-spacer>
            <v-btn @click="nextPage" v-if="currentPageIndex < pageComponents.length - 1">Next</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';

import Page1 from './pages/1.vue';
import Page2 from './pages/2.vue';
import Page3 from './pages/3.vue';
import Page4 from './pages/4.vue';
import Page6 from './pages/6.vue';
import Page7 from './pages/7.vue';
import Page8 from './pages/8.vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const traderStore = useTraderStore();
const { traderAttributes } = storeToRefs(traderStore);
const { initializeTrader } = traderStore;

const traderUuid = ref(route.params.traderUuid);
const sessionId = ref(route.params.sessionId);
const duration = ref(parseInt(route.params.duration) || 5);
const numRounds = ref(parseInt(route.params.numRounds) || 3);

const playerGoal = computed(() => {
  const trader = tradingSessionData.value?.human_traders?.find(t => t.id === traderUuid.value);
  return trader ? trader.goal : '';
});

onMounted(async () => {
  if (traderUuid.value && sessionId.value) {
    try {
      await initializeTrader(traderUuid.value);
      await traderStore.initializeTradingSystemWithPersistentSettings();
      await traderStore.getTraderAttributes(traderUuid.value);
    } catch (error) {
      console.error("Error initializing trader:", error);
    }
  } else {
    console.error("Trader UUID or Session ID not provided");
  }
});

const currentPageIndex = ref(0);

const pageComponents = [
  Page1,
  Page2,
  Page3,
  Page4,
  Page6,
  Page7,
  Page8,
].filter(component => component);

const pageTitles = [
  "Welcome",
  "Trading Platform",
  "Setup",
  "Your Earnings",
  "Other Participants in the Market",
  "Control Questions",
  "Practice"
];

const pageIcons = [
  "mdi-handshake",
  "mdi-monitor", // Changed from "mdi-desktop-mac" to "mdi-monitor"
  "mdi-cog",
  "mdi-cash",
  "mdi-account-group",
  "mdi-help-circle",
  "mdi-school"
];

// Define colors
const lightBlueColor = ref('light-blue');
const deepBlueColor = ref('deep-blue');

const nextPage = () => {
  if (currentPageIndex.value < pageComponents.length - 1) {
    currentPageIndex.value++;
  }
};

const prevPage = () => {
  if (currentPageIndex.value > 0) {
    currentPageIndex.value--;
  }
};

</script>

<style>
:root {
  --base-font-size: 14px;
}

.card-content {
  font-family: 'Inter', sans-serif;
  font-size: var(--base-font-size);
  line-height: 1.6;
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  background-color: #f8f9fa;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-section {
  background-color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.info-section h2 {
  font-size: 1.3rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
}

.highlight-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  font-size: 1rem;
  line-height: 1.4;
}

.highlight-box.warning { background-color: #FFF3E0; color: #E65100; }
.highlight-box.info { background-color: #E3F2FD; color: #1565C0; }
.highlight-box.success { background-color: #E8F5E9; color: #2E7D32; }

.dynamic-value {
  display: inline-block;
  padding: 2px 6px;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  color: #1976D2;
  font-weight: 500;
}

.text-h2 { font-size: 2.5em !important; }
.text-h4 { font-size: 1.75em !important; }
.text-h6 { font-size: 1.25em !important; }

.v-data-table {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.v-data-table th {
  font-weight: 600;
  color: #2c3e50;
  background-color: #f8f9fa;
}

.v-data-table td {
  color: #34495e;
}

.v-data-table .text-left {
  text-align: left;
}

/* Add this new style for the deep blue color */
.deep-blue {
  color: #1a237e !important; /* This is a deep blue color */
}

/* Update this new style for the light blue color */
.light-blue {
  color: #03a9f4 !important; /* This is a light blue color */
}

/* Remove or comment out the .light-blue--text class if it's not used elsewhere */
/* .light-blue--text {
  color: #03a9f4 !important;
} */
</style>