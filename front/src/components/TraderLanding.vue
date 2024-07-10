<template>
  <v-app>
    <v-main>
      <v-container fluid class="fill-height" @wheel="handleScroll">
        <v-row justify="center" align="center" class="fill-height">
          <v-col cols="12" md="10" lg="8" class="position-relative">
            <v-card 
              v-for="(component, index) in pageComponents" 
              :key="index"
              class="elevation-4 card-stack"
              :class="{ 'card-active': index === currentPageIndex }"
            >
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
                          {{ index + 1 }}: {{ pageTitles[index] }}
                        </h1>
                      </v-sheet>
                    </v-col>
                    <v-col cols="12">
                      <component :is="component" :goal="playerGoal" />
                    </v-col>
                  </v-row>
                </v-container>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

import Page1 from './pages/1.vue';
import Page2 from './pages/2.vue';
import Page3 from './pages/3.vue';
import Page4 from './pages/4.vue';
import Page5 from './pages/5.vue';
import Page6 from './pages/6.vue';
import Page7 from './pages/7.vue';
import Page8 from './pages/8.vue';

const props = defineProps({
  traderUuid: String,
});

const traderStore = useTraderStore();
const { gameParams, tradingSessionData } = storeToRefs(traderStore);

const playerGoal = computed(() => {
  const trader = tradingSessionData.value?.human_traders?.find(t => t.id === props.traderUuid);
  return trader ? trader.goal : '';
});

onMounted(async () => {
  if (props.traderUuid) {
    await traderStore.getTradingSessionData(props.traderUuid);
  }
});

const currentPageIndex = ref(0);
const scrollThreshold = 1200; 
let lastScrollTime = 0;
let accumulatedDelta = 0;

const handleScroll = (event) => {
  const now = new Date().getTime();
  if (now - lastScrollTime < 500) return;

  accumulatedDelta += event.deltaY;

  if (accumulatedDelta > scrollThreshold && currentPageIndex.value < pageComponents.length - 1) {
    currentPageIndex.value++;
    lastScrollTime = now;
    accumulatedDelta = 0;
  } else if (accumulatedDelta < -scrollThreshold && currentPageIndex.value > 0) {
    currentPageIndex.value--;
    lastScrollTime = now;
    accumulatedDelta = 0;
  }
};

const pageComponents = [
  Page1,
  Page2,
  Page3,
  Page4,
  Page5,
  Page6,
  Page7,
  Page8,
].filter(component => component);

const pageTitles = [
  "Welcome",
  "Trading Platform",
  "Setup",
  "Your Earnings (Selling)",
  "Your Earnings (Buying)",
  "Other Participants in the Market",
  "Control Questions",
  "Practice"
];

const duration = computed(() => gameParams.value.duration || '#');
const numMarkets = computed(() => gameParams.value.num_rounds || '#');
console.log(Object.keys(tradingSessionData.value));
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

<style scoped>
.position-relative {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
}
.card-stack {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  transform: translateY(-50%) translateY(20px);
  opacity: 0;
  transition: opacity 0.5s, transform 0.5s;
  pointer-events: none;
  max-height: 80vh;
  overflow-y: auto;
}
.card-active {
  opacity: 1;
  transform: translateY(-50%);
  pointer-events: auto;
}
</style>