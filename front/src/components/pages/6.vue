<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" :color="iconColor" class="pulse-icon">mdi-robot-industrial</v-icon>
        <h2 class="text-h4 gradient-text">Market Participants</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Main Info Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-robot</v-icon>
                  <span class="text-h6">Artificial Traders</span>
                </div>
                <p class="text-body-1">
                  The other participants in the market are all artificial (algorithmic) traders,
                  i.e., non-human.
                </p>
                <v-alert color="info" variant="tonal" border="start" class="mt-4">
                  All artificial traders have no objective in terms of earnings.
                  <br /><br />
                  However, they may have tasks such as buying or selling a specific number of
                  shares, or both.
                  <br /><br />
                  For example, their trading activity can significantly shift the price either
                  upward or downward.
                </v-alert>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Behavior Cards
        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-login</v-icon>
                  <span class="text-h6">Market Entry</span>
                </div>
                <p class="text-body-1">
                  Artificial traders join the market for the entire trading period.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card info-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="info" class="mr-2">mdi-swap-horizontal</v-icon>
                  <span class="text-h6">Trading Activity</span>
                </div>
                <p class="text-body-1">
                  They buy and sell during their time in the market, 
                  which can significantly shift the price either upward or downward.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <v-col cols="12" md="4">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card warning-gradient"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="warning" class="mr-2">mdi-logout</v-icon>
                  <span class="text-h6">Market Exit</span>
                </div>
                <p class="text-body-1">
                  They exit the market once they completed their task.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col> -->

        <!-- Next Steps Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" :color="iconColor" class="mr-2">mdi-school</v-icon>
                  <span class="text-h6">Next Steps</span>
                </div>
                <v-timeline density="compact" align="start">
                  <v-timeline-item dot-color="success" icon="mdi-checkbox-marked-circle">
                    <div class="text-subtitle-1 font-weight-bold">Control Questions</div>
                    <div class="text-body-2">You will answer some control questions</div>
                  </v-timeline-item>

                  <v-timeline-item dot-color="info" icon="mdi-play-circle">
                    <div class="text-subtitle-1 font-weight-bold">Market</div>
                    <div class="text-body-2">
                      You will start trading to familiarize yourself with the trading platform
                    </div>
                  </v-timeline-item>
                </v-timeline>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
const props = defineProps({
  iconColor: String,
})
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
  background: linear-gradient(45deg, #2196f3, #4caf50);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
  margin: 1rem 0;
}

.pulse-icon {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

.info-card {
  height: 100%;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.success-gradient {
  background: linear-gradient(135deg, #4caf5011, #81c78411) !important;
}

.info-gradient {
  background: linear-gradient(135deg, #2196f311, #64b5f611) !important;
}

.warning-gradient {
  background: linear-gradient(135deg, #ffa00011, #ffd54f11) !important;
}

@media (max-width: 960px) {
  .page-container {
    padding: 1rem;
  }
}
</style>
