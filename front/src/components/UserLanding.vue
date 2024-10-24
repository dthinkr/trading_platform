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
                      <v-icon left color="light-blue" large>{{ currentPageIcon }}</v-icon>
                      {{ currentPageTitle }}
                    </h2>
                  </div>
                </v-col>
                <v-col cols="12">
                  <router-view 
                    :traderAttributes="traderAttributes"
                    :iconColor="deepBlueColor"
                    @update:canProgress="canProgressFromQuestions = $event"
                  />
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions>
            <v-btn @click="prevPage" :disabled="isFirstPage">Previous</v-btn>
            <v-spacer></v-spacer>
            <v-btn 
              @click="nextPage" 
              v-if="!isLastPage"
              :disabled="shouldDisableNext"
            >
              Next
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const traderStore = useTraderStore();
const { traderAttributes } = storeToRefs(traderStore);
const { initializeTrader } = traderStore;

const traderUuid = ref(route.params.traderUuid);
const sessionId = ref(route.params.sessionId);

const pages = [
  { name: 'welcome', title: 'Welcome', icon: 'mdi-handshake' },
  { name: 'platform', title: 'Trading Platform', icon: 'mdi-monitor' },
  { name: 'setup', title: 'Setup', icon: 'mdi-cog' },
  { name: 'earnings', title: 'Your Earnings', icon: 'mdi-cash' },
  { name: 'participants', title: 'Other Participants', icon: 'mdi-account-group' },
  { name: 'questions', title: 'Control Questions', icon: 'mdi-help-circle' },
  { name: 'practice', title: 'Practice', icon: 'mdi-school' },
];

const currentPageIndex = computed(() => {
  return pages.findIndex(page => page.name === route.name);
});

const currentPageTitle = computed(() => {
  return pages[currentPageIndex.value]?.title || '';
});

const currentPageIcon = computed(() => {
  return pages[currentPageIndex.value]?.icon || '';
});

const isFirstPage = computed(() => currentPageIndex.value === 0);
const isLastPage = computed(() => currentPageIndex.value === pages.length - 1);

const nextPage = () => {
  if (!isLastPage.value) {
    const nextPageName = pages[currentPageIndex.value + 1].name;
    router.push({ 
      name: nextPageName,
      params: { sessionId: sessionId.value, traderUuid: traderUuid.value }
    });
  }
};

const prevPage = () => {
  if (!isFirstPage.value) {
    const prevPageName = pages[currentPageIndex.value - 1].name;
    router.push({ 
      name: prevPageName,
      params: { sessionId: sessionId.value, traderUuid: traderUuid.value }
    });
  }
};

const canProgressFromQuestions = ref(false);
const currentRouteName = computed(() => route.name);

// Add this computed property to handle Next button disabled state
const shouldDisableNext = computed(() => {
  return currentRouteName.value === 'questions' && !canProgressFromQuestions.value;
});

onMounted(async () => {
  if (traderUuid.value && sessionId.value) {
    try {
      await initializeTrader(traderUuid.value);
      await traderStore.initializeTradingSystemWithPersistentSettings();
      await traderStore.getTraderAttributes(traderUuid.value);
      
      // Redirect based on whether this is a persisted login or not
      if (!route.name || route.name === 'onboarding') {
        const targetRoute = authStore.isPersisted ? 'practice' : 'welcome';
        router.push({ 
          name: targetRoute,
          params: { sessionId: sessionId.value, traderUuid: traderUuid.value }
        });
      }
    } catch (error) {
      console.error("Error initializing trader:", error);
    }
  } else {
    console.error("Trader UUID or Session ID not provided");
  }
});

// Reset canProgressFromQuestions when leaving questions page
watch(currentRouteName, (newRoute, oldRoute) => {
  if (oldRoute === 'questions') {
    canProgressFromQuestions.value = false;
  }
});

// Define colors
const lightBlueColor = ref('light-blue');
const deepBlueColor = ref('deep-blue');
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
