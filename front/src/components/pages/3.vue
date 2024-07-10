<template>
  <div class="card-content">

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-text class="text-h5">
        <p class="mb-4">
          We are going to conduct <span class="font-weight-bold primary--text">{{ numMarkets }} markets</span> in which you will be a participant. You have a straightforward task:
        </p>
        <v-alert
          color="warning"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-alert"
          class="mb-4"
        >
          The task is to sell all your shares OR buy a given number. At the beginning of each market we will tell you to sell OR buy a given number of shares. You can only buy OR sell shares not both.
        </v-alert>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="primary" dark>
      <v-card-title class="text-h5">Your Objective</v-card-title>
      <v-card-text class="text-h5">
        <v-icon large left>mdi-target</v-icon>
        Sell at the highest price or buy at the lowest price.
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5">At the Beginning of Each Market</v-card-title>
      <v-card-text>
        <v-list-item two-line>
          <v-list-item-icon>
            <v-icon color="success">mdi-cash-multiple</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title class="text-h5">You will receive money</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
        <v-divider></v-divider>
        <v-list-item two-line>
          <v-list-item-icon>
            <v-icon color="info">mdi-file-document-multiple</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title class="text-h5">You will receive shares</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="secondary" dark>
      <v-card-text class="text-h5">
        <v-icon large left>mdi-information</v-icon>
        All trading will be in terms of Liras and the length of each market will be <span class="font-weight-bold">{{ duration }} minutes</span>.
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

const duration = computed(() => gameParams.value.duration || '#');
const numMarkets = computed(() => gameParams.value.num_rounds || '#');
</script>