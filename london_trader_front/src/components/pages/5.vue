<template>
  <div class="card-content">

    <v-card class="mb-6" elevation="3" shaped color="primary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-cart</v-icon>
        Automatic Buying
      </v-card-title>
      <v-card-text class="text-h5">
        <p>If your task is to buy {{ numShares }} shares:</p>
        <v-alert
          color="info"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-information"
          class="mt-3"
        >
          At the end of the market, the trading platform will automatically buy each unpurchased share (if any) at a price equal to one and a half (1.5) of the average best bid and ask price (mid-price) at the end of each market.
        </v-alert>
        <p class="mt-3">Loosely speaking, one and a half (1.5) of the market price at the end of the market.</p>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left color="green">mdi-calculator</v-icon>
        Market Earnings Calculation
      </v-card-title>
      <v-card-text class="text-h5">
        <v-alert
          color="success"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-cash"
          class="mb-3"
        >
          Market earnings = (Number of shares) * (mid-price at the beginning of the market) – total expense of purchases (incl. automatically bought shares)
        </v-alert>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="warning" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-alert</v-icon>
        Potential Losses
      </v-card-title>
      <v-card-text class="text-h5">
        <p>The market price might rise above the mid-price at the beginning of the market. If that happens, each purchase of a share will make a loss.</p>
        <v-alert
          color="error"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-arrow-up-bold"
          class="mt-3"
        >
          However, buying the shares is still in your interest as not buying them would create an even more significant loss.
        </v-alert>
        <p class="mt-3">To cover your losses, you will be given {{ initialLiras }} Liras at the beginning of each market.</p>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="secondary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-currency-gbp</v-icon>
        Final Earnings
      </v-card-title>
      <v-card-text class="text-h5">
        <p>At the end of the study, you will be awarded earnings from one randomly selected market.</p>
        <v-alert
          color="info"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-swap-horizontal"
          class="mt-3"
        >
          Your earnings in the chosen market are converted into GBP and paid to you. The conversion rate is {{ conversionRate }} Liras = 1 GBP.
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { gameParams } = storeToRefs(traderStore);

const numShares = computed(() => gameParams.value.num_shares || '#');
const initialLiras = computed(() => gameParams.value.initial_liras || '#');
const conversionRate = computed(() => gameParams.value.conversion_rate || 'X');
</script>