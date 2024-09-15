<template>
  <v-container fluid class="fill-height pa-0">
    <v-row justify="center" align="center" class="fill-height">
      <v-col cols="12" md="10" lg="8">
        <v-card class="elevation-4">
          <v-card-text>
            <v-container class="pa-0">
              <v-row no-gutters>
                <v-col cols="12">
                  <v-sheet
                    color="primary"
                    class="pa-12 mb-6"
                    rounded="lg"
                    elevation="4"
                  >
                    <h1 class="text-h2 font-weight-bold text-center white--text">
                      {{ pageTitles[currentPageIndex] }}
                    </h1>
                  </v-sheet>
                </v-col>
                <v-col cols="12">
                  <component 
                    :is="pageComponents[currentPageIndex]" 
                    :traderAttributes="traderAttributes"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions>
            <v-btn @click="prevPage" :disabled="currentPageIndex === 0">Previous</v-btn>
            <v-spacer></v-spacer>
            <v-btn @click="nextPage" v-if="currentPageIndex < pageComponents.length - 1">Next</v-btn>
            <v-btn @click="startTrading" v-else color="primary">Start Trading</v-btn>
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
const { initializeTrader } = traderStore;  // Add this line

const traderUuid = ref(route.params.traderUuid);
const sessionId = ref(route.params.sessionId);
const duration = ref(parseInt(route.params.duration) || 5);
const numRounds = ref(parseInt(route.params.numRounds) || 3);

const playerGoal = computed(() => {
  const trader = tradingSessionData.value?.human_traders?.find(t => t.id === traderUuid.value);
  return trader ? trader.goal : '';
});

onMounted(async () => {
  console.log("UserLanding mounted");
  console.log("traderUuid:", traderUuid.value);
  console.log("sessionId:", sessionId.value);

  if (traderUuid.value && sessionId.value) {
    try {
      console.log("Initializing trader...");
      await initializeTrader(traderUuid.value);
      console.log("Trader initialized");
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

console.log('TraderLanding mounted. Duration:', duration.value, 'NumRounds:', numRounds.value);

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

const startTrading = () => {
  router.push({ 
    name: 'trading',
    params: { 
      traderUuid: traderUuid.value,
      sessionId: sessionId.value
    } 
  });
};

</script>

<style>
:root {
  --base-font-size: 12px;
}

.card-content {
  font-size: var(--base-font-size);
  line-height: 1.6;
}

.text-h2 {
  font-size: 3em !important;
}

.text-h3 {
  font-size: 2.5em !important;
}

.text-h5 {
  font-size: 1.5em !important;
}

.text-h6 {
  font-size: 1.25em !important;
}
</style>