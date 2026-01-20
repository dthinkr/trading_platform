<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" color="primary" class="pulse-icon">mdi-finance</v-icon>
        <h2 class="text-h4 gradient-text">Financial Market Study</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <!-- Introduction Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <p class="text-body-1">
                  In this study, we investigate decision-making in financial markets. The following
                  are the instructions for this study. Please follow them carefully.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Earnings Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              class="info-card success-gradient"
              color="success-lighten-5"
            >
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="success" class="mr-2">mdi-cash-multiple</v-icon>
                  <span class="text-h6">Earnings</span>
                </div>
                <p class="text-body-1">
                  You can earn considerable money depending on your decisions. Your earnings will be
                  transferred to your Prolific account. The transfer may take a few working days.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Overview Card -->
        <v-col cols="12" md="6">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="primary" class="mr-2">mdi-information</v-icon>
                  <span class="text-h6">Study Overview</span>
                </div>
                <p class="text-body-1">
                  You will participate in markets where you can earn money by trading. Each market
                  will last <span class="highlight-text">{{ marketDuration }} minutes</span> and you
                  will participate in <span class="highlight-text">{{ numMarkets }} markets</span>.
                </p>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>

        <!-- Rules Card -->
        <v-col cols="12">
          <v-hover v-slot="{ isHovering, props }">
            <v-card v-bind="props" :elevation="isHovering ? 8 : 2" class="info-card">
              <v-card-text>
                <div class="d-flex align-center mb-4">
                  <v-icon size="28" color="primary" class="mr-2">mdi-clipboard-list</v-icon>
                  <span class="text-h6">After each market:</span>
                </div>
                <ul class="rules-list">
                  <li>All your remaining shares and money are converted to pounds sterling</li>
                  <li>You earn this amount from that market</li>
                  <li>A new market starts</li>
                  <li>
                    You cannot use your earnings from the previous market to trade in the following
                    markets
                  </li>
                </ul>
              </v-card-text>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTraderStore } from '@/store/app'

const traderStore = useTraderStore()

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0
})

const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.max_markets_per_human || 0
})
</script>

<style scoped>
/* Page-specific styles only - shared styles are in components.css */
</style>
