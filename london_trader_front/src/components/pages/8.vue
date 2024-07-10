<template>
  <div class="card-content">
    <v-card class="mb-6" elevation="3" shaped color="primary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-clock-outline</v-icon>
        Duration
      </v-card-title>
      <v-card-text class="text-h5">
        <p>Now you will practice using the trading platform for <span class="font-weight-bold">5 minutes</span>.</p>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-information-outline</v-icon>
        Important Rules
      </v-card-title>
      <v-card-text>
        <v-list-item two-line>
          <v-list-item-avatar>
            <v-icon color="warning" large>mdi-timer-sand</v-icon>
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title class="text-h5 font-weight-medium">Cancellation Policy</v-list-item-title>
            <v-list-item-subtitle class="text-h5">
                            When you place a passive order (bid or ask) you cannot cancel it for {{ cancelTime }} seconds. 
              After {{ cancelTime }} seconds have passed you can cancel it (if you want).
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>

        <v-divider class="my-4"></v-divider>

        <v-list-item two-line>
          <v-list-item-avatar>
            <v-icon color="info" large>mdi-file-document-multiple-outline</v-icon>
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title class="text-h5 font-weight-medium">Order Quantity</v-list-item-title>
            <v-list-item-subtitle class="text-h5">
              Each order is for one share only and you can choose the price. 
              If you want to place an order for a quantity of X shares at price P, you need to place X orders at price P.
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-card-text>
    </v-card>

    <v-card class="mb-6 start-trading-btn" elevation="3" shaped color="success" dark @click="startPractice">
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-play-circle-outline</v-icon>
        Ready to Start
      </v-card-title>
      <v-card-text class="text-h5">
        <p>You're now ready to begin your practice session. Good luck!</p>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter } from 'vue-router';

const router = useRouter();
const traderStore = useTraderStore();
const { gameParams } = storeToRefs(traderStore);

const cancelTime = computed(() => gameParams.value.cancel_time || '#');

const startPractice = () => {
  router.push({ name: 'TradingSystem', params: { traderUuid: traderStore.traderUuid } });
};
</script>

<style scoped>
.start-trading-btn {
  cursor: pointer;
  transition: transform 0.2s;
}
.start-trading-btn:hover {
  transform: scale(1.02);
}
</style>