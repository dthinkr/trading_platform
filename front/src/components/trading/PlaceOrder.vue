<template>
  <v-card height="100%" elevation="3" class="trading-panel">
    <!-- Sleep notification -->
    <div v-if="isNoiseTraderSleeping" class="sleep-notification">
      <v-icon color="orange" small class="mr-1">mdi-sleep</v-icon>
      Trading paused: Noise trader is sleeping
    </div>
    <div class="orders-container">
      <div class="order-column buy-column">
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
          :class="{ 'best-price': price === bestAsk, locked: !canBuy }"
        >
          <div class="order-content">
            <span class="order-type">BUY</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestAsk" color="primary" small>mdi-star</v-icon>
          </div>
          <v-btn
            @click="sendOrder('BUY', price)"
            :disabled="isBuyButtonDisabled || isGoalAchieved || !canBuy || isNoiseTraderSleeping"
            color="primary"
            small
          >
            Buy
          </v-btn>
        </div>
      </div>

      <div class="order-column sell-column">
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
          :class="{ 'best-price': price === bestBid, locked: !canSell }"
        >
          <div class="order-content">
            <span class="order-type">SELL</span>
            <div class="price">{{ formatPrice(price) }}</div>
            <v-icon v-if="price === bestBid" color="error" small>mdi-star</v-icon>
          </div>
          <v-btn
            @click="sendOrder('SELL', price)"
            :disabled="isSellButtonDisabled || isGoalAchieved || !canSell || isNoiseTraderSleeping"
            color="error"
            small
          >
            Sell
          </v-btn>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTraderStore } from '@/store/app'
import { useMarketStore } from '@/store/market'
import { storeToRefs } from 'pinia'

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false,
  },
  goalType: {
    type: String,
    default: 'free',
  },
})

const tradingStore = useTraderStore()
const marketStore = useMarketStore()
const { sendMessage } = tradingStore
const { gameParams, bidData, askData } = storeToRefs(tradingStore)
const { extraParams } = storeToRefs(marketStore)

const step = computed(() => gameParams.value.step || 1)
const hasAskData = computed(() => askData.value.length > 0)
const hasBidData = computed(() => bidData.value.length > 0)
const bestBid = computed(() =>
  hasBidData.value ? Math.max(...bidData.value.map((bid) => bid.x)) : null
)
const bestAsk = computed(() =>
  hasAskData.value ? Math.min(...askData.value.map((ask) => ask.x)) : null
)

const orderBookLevels = computed(() => gameParams.value.order_book_levels || 5)

const buyPrices = computed(() => {
  if (bestAsk.value === null || !orderBookLevels.value) {
    return Array.from(
      { length: orderBookLevels.value },
      (_, i) => bestBid.value + step.value * 1 - step.value * i
    )
  } else {
    return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i)
  }
})

// const buyPrices = computed(() => {
//   if (bestAsk.value === null || !orderBookLevels.value) return [];
//   return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i);
// });

// const sellPrices = computed(() => {
//   if (bestBid.value === null || !orderBookLevels.value) return [];
//   return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i);
// });

const sellPrices = computed(() => {
  if (bestBid.value === null || !orderBookLevels.value) {
    return Array.from(
      { length: orderBookLevels.value },
      (_, i) => bestAsk.value - step.value * 1 + step.value * i
    )
  } else {
    return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i)
  }
})

// const isBuyButtonDisabled = computed(() => !hasAskData.value);
const isBuyButtonDisabled = computed(() => {
  return false // Always keep Buy button enabled
})
//const isSellButtonDisabled = computed(() => !hasBidData.value);
const isSellButtonDisabled = computed(() => {
  return false // Always keep Buy button enabled
})

const isMobile = ref(false)

const canBuy = computed(() => props.goalType === 'buy' || props.goalType === 'free')
const canSell = computed(() => props.goalType === 'sell' || props.goalType === 'free')

// Check if noise trader is sleeping
const isNoiseTraderSleeping = computed(() => {
  const noiseTraderParam = extraParams.value.find(param => param.var_name === 'noise_trader_status')
  return noiseTraderParam?.value === 'sleeping'
})

function sendOrder(orderType, price) {
  if (
    !props.isGoalAchieved &&
    ((orderType === 'BUY' && canBuy.value) || (orderType === 'SELL' && canSell.value))
  ) {
    const newOrder = {
      id: Date.now().toString(),
      order_type: orderType,
      price: price,
      amount: 1, // You may want to adjust this or add an input for amount
      status: 'pending',
    }
    tradingStore.addOrder(newOrder)
  }
}

function getButtonColor(price, orderType) {
  if (orderType === 'buy') {
    return price === bestAsk.value ? 'primary' : 'grey lighten-3'
  } else if (orderType === 'sell') {
    return price === bestBid.value ? 'error' : 'grey lighten-3'
  }
}

function formatPrice(price) {
  return Math.round(price).toString()
}

function checkMobile() {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  )
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.trading-panel {
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  font-family: 'Inter', sans-serif;
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

.sleep-notification {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
  padding: 8px 12px;
  margin: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
}
</style>
