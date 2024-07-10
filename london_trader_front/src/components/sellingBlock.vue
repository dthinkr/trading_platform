<template>
  <v-card height="100%" elevation="3" class="trading-panel">
    <v-card-title class="cardtitle">
      <v-icon left color="white">mdi-chart-line</v-icon>
      Trading Panel
    </v-card-title>
    <v-card-subtitle class="subtitle">
      <v-icon color="warning" small class="mr-1">mdi-alert-circle</v-icon>
      Click highlighted buttons for immediate execution
    </v-card-subtitle>
    <v-card-text class="panel-content">
      <v-row no-gutters>
        <v-col cols="12" sm="6" class="order-column pr-sm-2">
          <h3 class="order-type-title">
            <v-icon left color="success">mdi-arrow-up-bold</v-icon>
            Buy Orders
          </h3>
          <v-btn
            v-for="(price, index) in buyPrices"
            :key="'buy-' + index"
            :disabled="isBuyButtonDisabled"
            @click="sendOrder(1, price)"
            :color="getButtonColor(price, 'buy')"
            :class="['order-btn', { 'best-price': price === bestAsk }]"
            elevation="2"
            block
            class="mb-2"
          >
            <span class="order-btn-text">Buy at {{ formatPrice(price) }}</span>
            <v-icon right v-if="price === bestAsk">mdi-star</v-icon>
          </v-btn>
        </v-col>
        <v-col cols="12" sm="6" class="order-column pl-sm-2">
          <h3 class="order-type-title">
            <v-icon left color="error">mdi-arrow-down-bold</v-icon>
            Sell Orders
          </h3>
          <v-btn
            v-for="(price, index) in sellPrices"
            :key="'sell-' + index"
            :disabled="isSellButtonDisabled"
            @click="sendOrder(-1, price)"
            :color="getButtonColor(price, 'sell')"
            :class="['order-btn', { 'best-price': price === bestBid }]"
            elevation="2"
            block
            class="mb-2"
          >
            <span class="order-btn-text">Sell for {{ formatPrice(price) }}</span>
            <v-icon right v-if="price === bestBid">mdi-star</v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>


<script setup>
import { computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const tradingStore = useTraderStore();
const { sendMessage } = tradingStore;
const { gameParams, bidData, askData } = storeToRefs(tradingStore);

const step = computed(() => gameParams.value.step);

const hasAskData = computed(() => askData.value.length > 0);
const hasBidData = computed(() => bidData.value.length > 0);

const bestBid = computed(() => hasBidData.value ? Math.max(...bidData.value.map(bid => bid.x)) : null);
const bestAsk = computed(() => hasAskData.value ? Math.min(...askData.value.map(ask => ask.x)) : null);

const buyPrices = computed(() => bestAsk.value !== null ? Array.from({ length: 5 }, (_, i) => bestAsk.value - step.value * i) : []);
const sellPrices = computed(() => bestBid.value !== null ? Array.from({ length: 5 }, (_, i) => bestBid.value + step.value * i) : []);

const isBuyButtonDisabled = computed(() => !hasAskData.value);
const isSellButtonDisabled = computed(() => !hasBidData.value);

function sendOrder(type, price) {
  sendMessage("add_order", { type, price, amount: 1 });
}

function getButtonColor(price, orderType) {
  if (orderType === "buy") {
    return price === bestAsk.value ? "primary" : "grey lighten-3";
  } else if (orderType === "sell") {
    return price === bestBid.value ? "error" : "grey lighten-3";
  }
}

function formatPrice(price) {
  return price.toFixed(2);
}
</script>

<style scoped>
.selling-block {
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
}

.cardtitle {
  font-size: 20px;
  font-weight: bold;
  background: linear-gradient(to right, #1a237e, #283593);
  color: white;
  padding: 16px;
}

.subtitle {
  font-size: 14px;
  color: #666;
  padding: 8px 16px;
  background-color: #e8eaf6;
}

.order-column {
  padding: 16px;
}

.order-type-title {
  font-size: 18px;
  font-weight: 500;
  color: #333;
  margin-bottom: 16px;
}

.order-btn {
  width: 100%;
  font-weight: 500;
  text-transform: none;
  transition: all 0.3s ease;
}

.order-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.best-price {
  font-weight: 700;
}

.best-price.v-btn--color-primary {
  background-color: #1565c0 !important;
  color: white !important;
}

.best-price.v-btn--color-error {
  background-color: #c62828 !important;
  color: white !important;
}
</style>