<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <CurrencyDollarIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Trading Panel
      </h3>
    </div>
    <div class="card-body">
      <div class="grid grid-cols-2 gap-4">
        <!-- Buy Orders Column -->
        <div class="space-y-3">
          <h4 class="text-sm font-medium text-neutral-700 flex items-center">
            <TrendingUpIcon class="h-4 w-4 mr-1 text-green-600" aria-hidden="true" />
            Buy Orders
          </h4>
          
          <div v-if="buyPrices.length === 0" class="text-sm text-neutral-500 p-3 bg-neutral-50 rounded-lg">
            No Buy Orders Available
            <div v-if="bestAsk" class="text-xs mt-1">
              Best Ask: <span class="font-mono">{{ formatPrice(bestAsk) }}</span>
            </div>
          </div>
          
          <div v-else class="space-y-2">
            <button
              v-for="(price, index) in buyPrices"
              :key="`buy-${index}`"
              @click="placeOrder('BUY', price)"
              :disabled="isBuyDisabled || isGoalAchieved || !canBuy"
              class="w-full p-3 rounded-lg border transition-all duration-200 focus:ring-2 focus:ring-offset-2"
              :class="getBuyButtonClass(price)"
              :aria-label="`Place buy order at ${formatPrice(price)}`"
            >
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium">BUY</span>
                <span class="font-mono font-semibold">{{ formatPrice(price) }}</span>
                <StarIcon 
                  v-if="price === bestAsk" 
                  class="h-3 w-3 text-yellow-500" 
                  aria-hidden="true" 
                />
              </div>
            </button>
          </div>
        </div>

        <!-- Sell Orders Column -->
        <div class="space-y-3">
          <h4 class="text-sm font-medium text-neutral-700 flex items-center">
            <TrendingDownIcon class="h-4 w-4 mr-1 text-red-600" aria-hidden="true" />
            Sell Orders
          </h4>
          
          <div v-if="sellPrices.length === 0" class="text-sm text-neutral-500 p-3 bg-neutral-50 rounded-lg">
            No Sell Orders Available
            <div v-if="bestBid" class="text-xs mt-1">
              Best Bid: <span class="font-mono">{{ formatPrice(bestBid) }}</span>
            </div>
          </div>
          
          <div v-else class="space-y-2">
            <button
              v-for="(price, index) in sellPrices"
              :key="`sell-${index}`"
              @click="placeOrder('SELL', price)"
              :disabled="isSellDisabled || isGoalAchieved || !canSell"
              class="w-full p-3 rounded-lg border transition-all duration-200 focus:ring-2 focus:ring-offset-2"
              :class="getSellButtonClass(price)"
              :aria-label="`Place sell order at ${formatPrice(price)}`"
            >
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium">SELL</span>
                <span class="font-mono font-semibold">{{ formatPrice(price) }}</span>
                <StarIcon 
                  v-if="price === bestBid" 
                  class="h-3 w-3 text-yellow-500" 
                  aria-hidden="true" 
                />
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Goal Achievement Message -->
      <div v-if="isGoalAchieved" class="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
        <div class="flex items-center">
          <CheckCircleIcon class="h-5 w-5 text-green-600 mr-2" aria-hidden="true" />
          <span class="text-sm font-medium text-green-800">
            Goal achieved! Trading disabled.
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  CurrencyDollarIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  StarIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false
  },
  goalType: {
    type: String,
    default: 'free'
  }
})

const tradingStore = useTradingStore()

// Computed properties
const step = computed(() => tradingStore.gameParams.step || 1000)
const orderBookLevels = computed(() => tradingStore.gameParams.order_book_levels || 5)

const bestBid = computed(() => {
  const bids = tradingStore.orderBook.bids
  return bids.length > 0 ? Math.max(...bids.map(bid => bid.x)) : null
})

const bestAsk = computed(() => {
  const asks = tradingStore.orderBook.asks
  return asks.length > 0 ? Math.min(...asks.map(ask => ask.x)) : null
})

const buyPrices = computed(() => {
  if (!bestAsk.value || !orderBookLevels.value) {
    return bestBid.value 
      ? Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value - step.value * i)
      : []
  }
  return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i)
})

const sellPrices = computed(() => {
  if (!bestBid.value || !orderBookLevels.value) {
    return bestAsk.value 
      ? Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value + step.value * i)
      : []
  }
  return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i)
})

const canBuy = computed(() => props.goalType === 'buy' || props.goalType === 'free')
const canSell = computed(() => props.goalType === 'sell' || props.goalType === 'free')

const isBuyDisabled = computed(() => false) // Always allow if other conditions met
const isSellDisabled = computed(() => false) // Always allow if other conditions met

// Methods
function formatPrice(price) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Math.round(price))
}

function getBuyButtonClass(price) {
  const isDisabled = isBuyDisabled.value || props.isGoalAchieved || !canBuy.value
  const isBest = price === bestAsk.value
  
  if (isDisabled) {
    return 'border-neutral-200 bg-neutral-100 text-neutral-400 cursor-not-allowed'
  }
  
  if (isBest) {
    return 'border-green-300 bg-green-50 text-green-800 hover:bg-green-100 focus:ring-green-500'
  }
  
  return 'border-green-200 bg-white text-green-700 hover:bg-green-50 focus:ring-green-500'
}

function getSellButtonClass(price) {
  const isDisabled = isSellDisabled.value || props.isGoalAchieved || !canSell.value
  const isBest = price === bestBid.value
  
  if (isDisabled) {
    return 'border-neutral-200 bg-neutral-100 text-neutral-400 cursor-not-allowed'
  }
  
  if (isBest) {
    return 'border-red-300 bg-red-50 text-red-800 hover:bg-red-100 focus:ring-red-500'
  }
  
  return 'border-red-200 bg-white text-red-700 hover:bg-red-50 focus:ring-red-500'
}

async function placeOrder(orderType, price) {
  if (props.isGoalAchieved) return
  if (orderType === 'BUY' && !canBuy.value) return
  if (orderType === 'SELL' && !canSell.value) return
  
  try {
    await tradingStore.placeOrder(orderType, price, 1)
  } catch (error) {
    console.error('Failed to place order:', error)
  }
}
</script>

<style scoped>
/* Component-specific styles if needed */
</style> 