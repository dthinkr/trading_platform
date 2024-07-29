<template>
  <v-card height="100%" elevation="3" class="trading-panel">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-chart-line</v-icon>
      Trading Panel
    </v-card-title>
    
    <div class="orders-container">
      <div class="order-column">
        <h3 class="order-type-title">
          <v-icon left color="primary">mdi-arrow-up-bold</v-icon>
          Buy Orders
        </h3>
        <div 
          v-for="(price, index) in buyPrices" 
          :key="'buy-' + index" 
          class="order-item bid"
          :class="{ 'best-price': price === bestAsk }"
          @mousedown="startOrderAdjustment(1, price, $event)"
          @touchstart.prevent="startOrderAdjustment(1, price, $event)"
        >
          <div class="order-content">
            <span class="order-type">BUY</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestAsk" color="primary" small>mdi-star</v-icon>
          </div>
        </div>
      </div>
      
      <div class="order-column">
        <h3 class="order-type-title">
          <v-icon left color="error">mdi-arrow-down-bold</v-icon>
          Sell Orders
        </h3>
        <div 
          v-for="(price, index) in sellPrices" 
          :key="'sell-' + index" 
          class="order-item ask"
          :class="{ 'best-price': price === bestBid }"
          @mousedown="startOrderAdjustment(-1, price, $event)"
          @touchstart.prevent="startOrderAdjustment(-1, price, $event)"
        >
          <div class="order-content">
            <span class="order-type">SELL</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestBid" color="error" small>mdi-star</v-icon>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="isAdjusting" 
         class="order-adjustment-overlay" 
         @mousemove="adjustOrderAmount"
         @touchmove.prevent="adjustOrderAmount"
         @mouseup="finishOrder" 
         @touchend.prevent="finishOrder"
         @mouseleave="cancelOrder"
         @touchcancel="cancelOrder">
      <div class="order-adjustment-content" :class="orderType === 1 ? 'buy-order' : 'sell-order'">
        <h2>{{ orderType === 1 ? 'Buy' : 'Sell' }} Order</h2>
        <p class="price">Price: {{ formatPrice(orderPrice) }}</p>
        <p class="amount">Amount: {{ Math.abs(orderAmount) }}</p>
        <div class="adjustment-guide">
          <div class="guide-line"></div>
          <div class="guide-center"></div>
          <div class="guide-cursor" :style="{ left: cursorPosition.x + 'px', top: cursorPosition.y + 'px' }"></div>
          <div class="guide-zones">
            <div v-for="(zone, index) in guideZones" :key="index" class="guide-zone" :style="zoneStyle(zone)"></div>
          </div>
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

const step = computed(() => gameParams.value.step);
const hasAskData = computed(() => askData.value.length > 0);
const hasBidData = computed(() => bidData.value.length > 0);
const bestBid = computed(() => hasBidData.value ? Math.max(...bidData.value.map(bid => bid.x)) : null);
const bestAsk = computed(() => hasAskData.value ? Math.min(...askData.value.map(ask => ask.x)) : null);
const buyPrices = computed(() => bestAsk.value !== null ? Array.from({ length: 5 }, (_, i) => bestAsk.value - step.value * i) : []);
const sellPrices = computed(() => bestBid.value !== null ? Array.from({ length: 5 }, (_, i) => bestBid.value + step.value * i) : []);
const isBuyButtonDisabled = computed(() => !hasAskData.value);
const isSellButtonDisabled = computed(() => !hasBidData.value);

const isMobile = ref(false);

const isAdjusting = ref(false);
const orderType = ref(null);
const orderPrice = ref(null);
const orderAmount = ref(0);
const startX = ref(0);
const startY = ref(0);
const cursorPosition = ref({ x: 100, y: 100 });
const guideZones = [
  { radius: 40, amount: 0 },
  { radius: 60, amount: 1 },
  { radius: 80, amount: 5 },
  { radius: 90, amount: 10 },
  { radius: 100, amount: 15 },
];

function startOrderAdjustment(type, price, event) {
  isAdjusting.value = true;
  orderType.value = type;
  orderPrice.value = price;
  orderAmount.value = 0;
  const clientX = event.clientX || (event.touches && event.touches[0].clientX);
  const clientY = event.clientY || (event.touches && event.touches[0].clientY);
  startX.value = clientX;
  startY.value = clientY;
  cursorPosition.value = { x: 100, y: 100 };
}

function adjustOrderAmount(event) {
  if (!isAdjusting.value) return;
  const clientX = event.clientX || (event.touches && event.touches[0].clientX);
  const clientY = event.clientY || (event.touches && event.touches[0].clientY);
  const deltaX = clientX - startX.value;
  const deltaY = startY.value - clientY;
  const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  const angle = Math.atan2(deltaY, deltaX);
  
  const zoneIndex = guideZones.findIndex(zone => distance <= zone.radius);
  orderAmount.value = (zoneIndex >= 0 ? guideZones[zoneIndex].amount : guideZones[guideZones.length - 1].amount) * (orderType.value === 1 ? 1 : -1);
  
  cursorPosition.value = {
    x: 100 + Math.cos(angle) * Math.min(distance, 100),
    y: 100 - Math.sin(angle) * Math.min(distance, 100)
  };
}

function zoneStyle(zone) {
  return {
    width: `${zone.radius * 2}px`,
    height: `${zone.radius * 2}px`,
    left: `${100 - zone.radius}px`,
    top: `${100 - zone.radius}px`,
  };
}

function finishOrder() {
  if (isAdjusting.value && orderAmount.value !== 0) {
    sendMessage("add_order", { type: orderType.value, price: orderPrice.value, amount: Math.abs(orderAmount.value) });
  }
  cancelOrder();
}

function cancelOrder() {
  isAdjusting.value = false;
  orderType.value = null;
  orderPrice.value = null;
  orderAmount.value = 0;
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

function checkMobile() {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

onMounted(() => {
  checkMobile();
  window.addEventListener('resize', checkMobile);
  if (!isMobile.value) {
    document.addEventListener('mouseleave', cancelOrder);
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile);
  if (!isMobile.value) {
    document.removeEventListener('mouseleave', cancelOrder);
  }
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
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.order-adjustment-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.order-adjustment-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 90%;
  max-height: 90%;
  overflow: auto;
}

.buy-order {
  border-left: 4px solid #2196F3;
}

.sell-order {
  border-left: 4px solid #F44336;
}

.adjustment-guide {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 20px auto;
  border: 2px solid #ccc;
  border-radius: 50%;
}

.guide-line, .guide-center, .guide-cursor, .guide-zone {
  position: absolute;
}

.guide-line {
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #ccc;
}

.guide-center {
  top: 50%;
  left: 50%;
  width: 10px;
  height: 10px;
  background-color: #333;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.guide-cursor {
  width: 20px;
  height: 20px;
  background-color: #2196F3;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.guide-zone {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
}
</style>