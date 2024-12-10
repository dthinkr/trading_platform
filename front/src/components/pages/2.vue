<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-monitor-dashboard</v-icon>
        <h2 class="text-h4 gradient-text">Trading Platform Guide</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Introduction Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-monitor</v-icon>
                  <span class="text-h6">What is the Trading Platform?</span>
                </div>
                <p class="text-body-1">
                  The trading platform is software that allows you to trade with other participants. 
                  It shows relevant information about the demand and supply of an asset (e.g. a share). 
                  What you see on the trading platform is common knowledge i.e. all other participants can see it.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Orders Section -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-flash</v-icon>
                  <span class="text-h6">Direct Orders</span>
                </div>
                <p class="text-body-1">
                  You can directly accept an existing price to sell or buy, such as an order from another participant. 
                  In this case, the trade is immediately executed at the best bid or ask respectively.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card info-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="info" class="mr-2">mdi-clock</v-icon>
                  <span class="text-h6">Passive Orders</span>
                </div>
                <p class="text-body-1">
                  You can place orders to sell or buy that are not immediately executed. 
                  This means you have to wait for someone to accept them.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Improving Orders -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-trending-up</v-icon>
                  <span class="text-h6">Improving Orders</span>
                </div>
                <v-list class="improvement-list">
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon color="success">mdi-arrow-down</v-icon>
                    </template>
                    Place an order to sell (ask) a share for a lower price than the current best ask
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon color="error">mdi-arrow-up</v-icon>
                    </template>
                    Place an order to buy (bid) a share for a higher price than the current best bid
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Demo Section -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-play-circle</v-icon>
                  <span class="text-h6">Platform Demo</span>
                </div>
                <v-img
                  :src="demoGif"
                  alt="Trading Platform Demo"
                  max-width="600"
                  contain
                  class="mx-auto rounded-lg"
                ></v-img>
                <p class="text-body-2 text-center mt-4 font-italic">
                  This demonstration shows the key features of the trading platform in action
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
import demoGif from '@/assets/demo.gif';

const props = defineProps({
  iconColor: String
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

.improvement-list {
  background: transparent !important;
}

.improvement-list .v-list-item {
  min-height: 44px;
  padding: 0.5rem;
  transition: all 0.3s ease;
}

.improvement-list .v-list-item:hover {
  background: rgba(0,0,0,0.03);
  transform: translateX(5px);
}

@media (max-width: 960px) {
  .page-container {
    padding: 1rem;
  }
}
</style>