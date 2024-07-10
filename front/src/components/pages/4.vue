<template>
  <div class="card-content">

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left color="warning">mdi-clock-alert</v-icon>
        Time Limit Not Met
      </v-card-title>
      <v-card-text class="text-h5">
        If you do not achieve the objective within the time limit of the market, the trading platform will automatically execute additional trades.
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="primary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-sale</v-icon>
        Automatic Selling
      </v-card-title>
      <v-card-text class="text-h5">
        <p>If your task is to sell {{ numShares }} shares:</p>
        <v-alert
          color="info"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-information"
          class="mt-3"
        >
          At the end of the market, the trading platform will automatically sell each unsold share (if any) at a price equal to half of the average best bid and ask price (mid-price) at the end of each market.
        </v-alert>
        <p class="mt-3">Loosely speaking, half of the market price at the end of the market.</p>
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
          Market earnings = revenue from sales (incl. automatically sold shares) – (Number of shares) * (mid-price at the beginning of the market)
        </v-alert>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="warning" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-alert</v-icon>
        Potential Losses
      </v-card-title>
      <v-card-text class="text-h5">
        <p>The market price might drop below the mid-price at the beginning of the market. If that happens, each sale of a share will make a loss.</p>
        <v-alert
          color="error"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-arrow-down-bold"
          class="mt-3"
        >
          However, selling the shares is still in your interest as keeping them would create an even more significant loss.
        </v-alert>
        <p class="mt-3">To cover your losses, you will be given {{ initialLiras }} Liras at the beginning of each market.</p>
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
</script>