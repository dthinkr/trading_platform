<template>
  <div class="trading-panel">
    <div class="orders-container">
      <div class="order-column buy-column">
        <h3 class="order-type-title">
          <svg class="w-4 h-4 inline mr-2 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Buy Orders
        </h3>
        <div v-if="buyPrices.length === 0" class="text-sm text-gray-500">
          No Buy Orders
          <div v-if="bestAsk !== null">Best Ask Price: {{ formatPrice(bestAsk) }}</div>
        </div>
        <div 
          v-for="(price, index) in buyPrices" 
          :key="'buy-' + index" 
          class="order-item bid"
          :class="{ 'best-price': price === bestAsk, 'locked': !canBuy }"
        >
          <div class="order-content">
            <span class="order-type">BUY</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <svg v-if="price === bestAsk" class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </div>
          <button 
            @click="sendOrder('BUY', price)" 
            :disabled="isBuyButtonDisabled || isGoalAchieved || !canBuy" 
            class="btn-buy"
          >
            Buy
          </button>
        </div>
      </div>
      
      <div class="order-column sell-column">
        <h3 class="order-type-title">
          <svg class="w-4 h-4 inline mr-2 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M5 10a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1z" clip-rule="evenodd" />
          </svg>
          Sell Orders
        </h3>
        <div v-if="sellPrices.length === 0" class="text-sm text-gray-500">
          No Sell Orders
          <div v-if="bestBid !== null">Best Bid Price: {{ formatPrice(bestBid) }}</div>
        </div>
        <div 
          v-for="(price, index) in sellPrices" 
          :key="'sell-' + index" 
          class="order-item ask"
          :class="{ 'best-price': price === bestBid, 'locked': !canSell }"
        >
          <div class="order-content">
            <span class="order-type">SELL</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <svg v-if="price === bestBid" class="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </div>
          <button 
            @click="sendOrder('SELL', price)" 
            :disabled="isSellButtonDisabled || isGoalAchieved || !canSell" 
            class="btn-sell"
          >
            Sell
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import { useTradingStore } from "@/stores/trading";
import { storeToRefs } from "pinia";

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false
  },
  goalType: {
    type: String,
    default: 'free'
  }
});

const tradingStore = useTradingStore();
const { orderBook, gameParams } = storeToRefs(tradingStore);

const step = computed(() => gameParams.value?.step || 1);
const hasAskData = computed(() => orderBook.value?.asks && orderBook.value.asks.length > 0);
const hasBidData = computed(() => orderBook.value?.bids && orderBook.value.bids.length > 0);
const bestBid = computed(() => {
  if (!hasBidData.value) return null;
  console.log('DEBUG: Processing bids:', orderBook.value.bids);
  
  // Handle different bid structures
  const bids = orderBook.value.bids;
  let prices = [];
  
  if (bids.length > 0) {
    // Check if bids have 'price' property, 'x' property, or are just numbers
    const firstBid = bids[0];
    if (typeof firstBid === 'object' && firstBid.price !== undefined) {
      prices = bids.map(bid => Number(bid.price)).filter(p => !isNaN(p));
    } else if (typeof firstBid === 'object' && firstBid.x !== undefined) {
      prices = bids.map(bid => Number(bid.x)).filter(p => !isNaN(p));
    } else if (typeof firstBid === 'number') {
      prices = bids.map(bid => Number(bid)).filter(p => !isNaN(p));
    } else {
      console.log('DEBUG: Unknown bid structure:', firstBid);
    }
  }
  
  console.log('DEBUG: Extracted bid prices:', prices);
  return prices.length > 0 ? Math.max(...prices) : null;
});
const bestAsk = computed(() => {
  if (!hasAskData.value) return null;
  console.log('DEBUG: Processing asks:', orderBook.value.asks);
  
  // Handle different ask structures
  const asks = orderBook.value.asks;
  let prices = [];
  
  if (asks.length > 0) {
    // Check if asks have 'price' property, 'x' property, or are just numbers
    const firstAsk = asks[0];
    if (typeof firstAsk === 'object' && firstAsk.price !== undefined) {
      prices = asks.map(ask => Number(ask.price)).filter(p => !isNaN(p));
    } else if (typeof firstAsk === 'object' && firstAsk.x !== undefined) {
      prices = asks.map(ask => Number(ask.x)).filter(p => !isNaN(p));
    } else if (typeof firstAsk === 'number') {
      prices = asks.map(ask => Number(ask)).filter(p => !isNaN(p));
    } else {
      console.log('DEBUG: Unknown ask structure:', firstAsk);
    }
  }
  
  console.log('DEBUG: Extracted ask prices:', prices);
  return prices.length > 0 ? Math.min(...prices) : null;
});

const orderBookLevels = computed(() => {
  const levels = gameParams.value?.order_book_levels || 5;
  return Math.max(1, Number(levels) || 5); // Ensure it's a valid number
});

// Use default price if no order book data is available
const defaultPrice = computed(() => {
  const price = gameParams.value?.default_price || 100;
  return Number(price) || 100; // Ensure it's a valid number
});

const buyPrices = computed(() => {
  if (!orderBookLevels.value) return [];
  
  let referencePrice;
  
  if (bestAsk.value !== null && !isNaN(bestAsk.value)) {
    // Normal case: use bestAsk as reference
    referencePrice = bestAsk.value;
  } else if (bestBid.value !== null && !isNaN(bestBid.value)) {
    // If no asks, use bestBid as reference
    referencePrice = bestBid.value;
  } else {
    // If no order book data, use default price
    referencePrice = defaultPrice.value;
  }
  
  const stepValue = Number(step.value) || 1;
  
  // Generate price levels: reference price and below
  return Array.from({ length: orderBookLevels.value }, (_, i) => {
    const price = referencePrice - (stepValue * i);
    return Math.max(1, Math.round(price)); // Ensure minimum price of 1
  });
});

const sellPrices = computed(() => {
  if (!orderBookLevels.value) return [];
  
  let referencePrice;
  
  if (bestBid.value !== null && !isNaN(bestBid.value)) {
    // Normal case: use bestBid as reference
    referencePrice = bestBid.value;
  } else if (bestAsk.value !== null && !isNaN(bestAsk.value)) {
    // If no bids, use bestAsk as reference  
    referencePrice = bestAsk.value;
  } else {
    // If no order book data, use default price
    referencePrice = defaultPrice.value;
  }
  
  const stepValue = Number(step.value) || 1;
  
  // Generate price levels: reference price and above
  return Array.from({ length: orderBookLevels.value }, (_, i) => {
    const price = referencePrice + (stepValue * i);
    return Math.round(price);
  });
});

const isBuyButtonDisabled = computed(() => {
  return false;  // Always keep Buy button enabled
});

const isSellButtonDisabled = computed(() => {
  return false;  // Always keep Sell button enabled
});

const isMobile = ref(false);

const canBuy = computed(() => props.goalType === 'buy' || props.goalType === 'free');
const canSell = computed(() => props.goalType === 'sell' || props.goalType === 'free');

async function sendOrder(orderType, price) {
  if (!props.isGoalAchieved && ((orderType === 'BUY' && canBuy.value) || (orderType === 'SELL' && canSell.value))) {
    const order = {
      order_type: orderType === 'BUY' ? 1 : 0, // Convert to OrderType enum values
      price: price,
      amount: 1
    };
    
    try {
      await tradingStore.placeOrder(order);
    } catch (error) {
      console.error('Failed to place order:', error);
    }
  }
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

// Debug the data coming from the store
watch([gameParams, orderBook], ([newGameParams, newOrderBook]) => {
  console.log('PlaceOrder - gameParams:', newGameParams);
  console.log('PlaceOrder - orderBook:', newOrderBook);
  console.log('PlaceOrder - bestBid:', bestBid.value);
  console.log('PlaceOrder - bestAsk:', bestAsk.value);
  console.log('PlaceOrder - defaultPrice:', defaultPrice.value);
  console.log('PlaceOrder - buyPrices:', buyPrices.value);
  console.log('PlaceOrder - sellPrices:', sellPrices.value);
}, { immediate: true, deep: true });


</script>

<style scoped>
.trading-panel {
  display: flex;
  flex-direction: column;
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  height: 100%;
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  justify-content: space-between;
}

.order-column {
  flex: 0 0 48%; /* Adjust the width as needed */
}

.order-type-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.order-item {
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 4px;
}

.order-item.bid {
  background-color: rgba(33, 150, 243, 0.1);
}

.order-item.ask {
  background-color: rgba(244, 67, 54, 0.1);
}

.order-type {
  font-size: 11px;
  font-weight: 500;
}

.price {
  font-size: 14px;
  font-weight: 600;
}

.order-content {
  display: flex;
  align-items: center;
}

.order-content > * {
  margin-right: 8px;
}

.best-price {
  font-weight: bold;
}

.locked {
  opacity: 0.5;
}

/* Button styling to match Vuetify appearance */
.btn-buy, .btn-sell {
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 64px;
}

.btn-buy {
  background-color: #2196F3;
  color: white;
}

.btn-buy:hover:not(:disabled) {
  background-color: #1976D2;
}

.btn-buy:disabled {
  background-color: #cccccc;
  color: #666666;
  cursor: not-allowed;
}

.btn-sell {
  background-color: #F44336;
  color: white;
}

.btn-sell:hover:not(:disabled) {
  background-color: #D32F2F;
}

.btn-sell:disabled {
  background-color: #cccccc;
  color: #666666;
  cursor: not-allowed;
}
</style>