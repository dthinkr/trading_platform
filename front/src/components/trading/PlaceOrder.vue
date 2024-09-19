<template>
  <v-card height="100%" elevation="3" class="trading-panel">
    
    <div class="orders-container">
      <div class="order-column">
        <h3 class="order-type-title">
          <v-icon left color="primary">mdi-arrow-up-bold</v-icon>
          Buy Orders
        </h3>
        <div v-if="buyPrices.length === 0">
          No Buy Orders
          <div v-if="bestAsk !== null">Best Ask Price: {{ formatPrice(bestAsk) }}</div>
        </div>
        <div 
          v-for="(price, index) in buyPrices" 
          :key="'buy-' + index" 
          class="order-item bid"
          :class="{ 'best-price': price === bestAsk }"
        >
          <div class="order-content">
            <span class="order-type">BUY</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestAsk" color="primary" small>mdi-star</v-icon>
          </div>
          <v-btn @click="sendOrder('BUY', price)" :disabled="isBuyButtonDisabled" color="primary" small>Buy</v-btn>
        </div>
      </div>
      
      <div class="order-column">
        <h3 class="order-type-title">
          <v-icon left color="error">mdi-arrow-down-bold</v-icon>
          Sell Orders
        </h3>
        <div v-if="sellPrices.length === 0">
          No Sell Orders
          <div v-if="bestBid !== null">Best Bid Price: {{ formatPrice(bestBid) }}</div>
        </div>
        <div 
          v-for="(price, index) in sellPrices" 
          :key="'sell-' + index" 
          class="order-item ask"
          :class="{ 'best-price': price === bestBid }"
        >
          <div class="order-content">
            <span class="order-type">SELL</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestBid" color="error" small>mdi-star</v-icon>
          </div>
          <v-btn @click="sendOrder('SELL', price)" :disabled="isSellButtonDisabled" color="error" small>Sell</v-btn>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const tradingStore = useTraderStore();
const { sendMessage } = tradingStore;
const { gameParams, bidData, askData } = storeToRefs(tradingStore);

const step = computed(() => gameParams.value.step || 1);
const hasAskData = computed(() => askData.value.length > 0);
const hasBidData = computed(() => bidData.value.length > 0);
const bestBid = computed(() => hasBidData.value ? Math.max(...bidData.value.map(bid => bid.x)) : null);
const bestAsk = computed(() => hasAskData.value ? Math.min(...askData.value.map(ask => ask.x)) : null);

const orderBookLevels = computed(() => gameParams.value.order_book_levels || 5);

const buyPrices = computed(() => {
  if (bestAsk.value === null || !orderBookLevels.value) return [];
  return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i);
});

const sellPrices = computed(() => {
  if (bestBid.value === null || !orderBookLevels.value) return [];
  return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i);
});

const isBuyButtonDisabled = computed(() => !hasAskData.value);
const isSellButtonDisabled = computed(() => !hasBidData.value);

const isMobile = ref(false);

function sendOrder(orderType, price) {
  const newOrder = {
    id: Date.now().toString(),
    order_type: orderType,
    price: price,
    amount: 1, // You may want to adjust this or add an input for amount
    status: 'pending'
  };
  tradingStore.addOrder(newOrder);
}

function getButtonColor(price, orderType) {
  if (orderType === "buy") {
    return price === bestAsk.value ? "primary" : "grey lighten-3";
  } else if (orderType === "sell") {
    return price === bestBid.value ? "error" : "grey lighten-3";
  }
}

function formatPrice(price) {
  return Math.round(price).toString();
}

function checkMobile() {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

onMounted(() => {
  checkMobile();
  window.addEventListener('resize', checkMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile);
});
</script>

<style scoped>
.trading-panel {
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
}

.cardtitle-primary {
  color: black;
  font-weight: bold;
  padding: 12px 16px;
}

.subtitle {
  font-size: 0.9rem;
  color: #666;
  padding: 0 16px 12px;
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.order-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-type-title {
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.order-item {
  background-color: white;
  border-radius: 8px;
  padding: 8px 12px;
  position: relative;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  cursor: pointer;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.order-item.bid {
  border-left: 4px solid #2196F3;
}

.order-item.ask {
  border-left: 4px solid #F44336;
}

.order-item.best-price {
  background-color: #E3F2FD;
}

.order-content {
  flex-grow: 1;
}

.order-type {
  font-weight: bold;
  text-transform: uppercase;
  font-size: 0.8rem;
  color: #666;
}

.price {
  font-size: 1.1rem;
  font-weight: bold;
  color: #333;
}
</style>