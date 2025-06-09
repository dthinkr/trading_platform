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
                    <li style="margin-bottom: 10px; margin-top: 10px;">Buy a certain number of shares at the lowest price. (Informed Trader)</li>
                    <li style="margin-bottom: 10px;">Sell a certain number of shares at the highest price. (Informed Trader)</li>
                    <li>Buy and Sell shares to generate profit. (Speculator)</li>
                  </ul>
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
                  <span class="text-h6">Task as a Informed Trader</span>
                </div>
                <div class="text-body-1 font-weight-medium">
                  In this role, your task is to buy or sell a specific number of shares.
                  <br><br>
                  At the beginning of each market, you will be given a specific number of shares.
                  <br><br>
                  By the end of the market, you must ensure that you have achieved your goal.
                  <br><br>
                  <div style="border: 1px solid #f44336; background-color: #fdecea; color: #b71c1c; padding: 16px; border-radius: 8px; font-family: sans-serif;">
                  <strong>Important Notice:</strong>
                  <br><br>
                  If, at the end of each market, you haven't completed your task, the platform will automatically buy or sell the remaining shares at a penalized price. 
                  This will affect your profits.
                  </div>
                </div>
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
                  <span class="text-h6">Task as a Speculator</span>
                </div>
                <div class="text-body-1 font-weight-medium">
                  In this role, your task is to buy and sell shares in order to make profits.
                  <br><br>
                  At the beginning of each market, you will be given a specific number of shares.
                  <br><br>
                  By the end of the market, you must ensure that the number of shares matches the initial number you were given.
                  <br><br>

                  <div style="border: 1px solid #f44336; background-color: #fdecea; color: #b71c1c; padding: 16px; border-radius: 8px; font-family: sans-serif;">
                  <strong>Important Notice:</strong>
                  <br><br>
                  If, at the end of each market, the number of shares held differs from the initial amount, the platform will restore the original balance by buying or selling shares at the the <strong>Initial Midprice</strong>.
                  <br><br>
                  This is very likely to result in a loss.
                  <br><br>
                  <strong>Example 1</strong>
                  <br>
                  Initial Midprice = 100 Liras
                  <br>
                  Initial Shares = 100
                  <br>
                  Shares at the end of the market = 110
                  <br>
                  The 10 excess shares (110 - 100) were purchased at an average price of 120 Liras.
                  <br>
                  The platform liquidates these 10 shares at the initial midprice of 100 Liras.
                  <br>
                  Loss = 10 shares × (100 - 120) = -200 Liras
                  <br><br>
                  <strong>Example 2</strong>
                  <br>
                  Initial Midprice = 100 Liras
                  <br>
                  Initial Shares = 100
                  <br>
                  Shares at the end of the market = 90
                  <br>
                  The 10 missing shares (100 - 90) were sold at an average price of 80 Liras.
                  <br>
                  The platform purchases these 10 shares at the initial midprice of 100 Liras.
                  <br>
                  Loss = 10 shares × (80 - 100) = -200 Liras
                  </div>
                </div>
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