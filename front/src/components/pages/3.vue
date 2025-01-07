<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-target</v-icon>
        <h2 class="text-h4 gradient-text">General Trading Objectives</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Overview Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-information</v-icon>
                  <span class="text-h6">Overview</span>
                </div>
                <p class="text-body-1">
                  We are going to conduct <span class="highlight-text">{{ numMarkets }} markets</span> 
                  in which you will have a straightforward task. 
                  <br><br>
                  The <span style="font-weight: bold; color: #1976D2; ">first market</span> is a practice market and will therefore not affect 
                  your final earnings.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Task Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card warning-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="warning" class="mr-2">mdi-alert</v-icon>
                  <span class="text-h6">Your Task</span>
                </div>
                <p class="text-body-1 font-weight-medium">
                  At the beginning of each market you will be given a specific role.
                  <br><br>
                  Potential tasks for your role could include:
                  <ul style="margin-left: 20px;">
                    <li style="margin-bottom: 10px; margin-top: 10px;">Buy a certain number of shares at the lowest price.</li>
                    <li style="margin-bottom: 10px;">Sell a certain number of shares at the highest price.</li>
                    <li>Buy and Sell shares to generate profit.</li>
                  </ul>
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Objective Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-target</v-icon>
                  <span class="text-h6">Your Objective</span>
                </div>
                <p class="text-body-1 font-weight-medium">
                  Sell at the highest price or buy at the lowest price.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Market Details Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card info-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="info" class="mr-2">mdi-clock-outline</v-icon>
                  <span class="text-h6">Market Details</span>
                </div>
                <p class="text-body-1">
                  All trading will be in terms of Liras and the length of each market will be 
                  <span class="highlight-text">{{ marketDuration }} minutes</span>.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";

const props = defineProps({
  iconColor: String
});

const traderStore = useTraderStore();

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0;
});

const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.max_markets_per_human || 0;
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

.success-gradient {
  background: linear-gradient(135deg, #4CAF5011, #81C78411) !important;
}

.info-gradient {
  background: linear-gradient(135deg, #2196F311, #64B5F611) !important;
}

.warning-gradient {
  background: linear-gradient(135deg, #FFA00011, #FFD54F11) !important;
}

.highlight-text {
  color: #1976D2;
  font-weight: 600;
  font-size: 1.1rem;
}

@media (max-width: 960px) {
  .page-container {
    padding: 1rem;
  }
}
</style>