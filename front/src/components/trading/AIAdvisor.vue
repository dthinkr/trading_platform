<template>
  <div class="ai-advisor-banner">
    <div v-if="!advice" class="waiting-advice">
      <Bot :size="20" class="advisor-icon pulse" />
      <span>AI advisor is analyzing the market...</span>
    </div>
    
    <div v-else class="advice-content">
      <div class="advice-left">
        <Bot :size="20" class="advisor-icon" />
        <span class="advice-label">AI Suggestion</span>
      </div>
      
      <div class="advice-center">
        <div class="advice-action" :class="actionClass">
          <component :is="actionIcon" :size="16" class="action-icon" />
          <span class="action-text">{{ actionText }}</span>
        </div>
        
        <div v-if="advice.reasoning" class="advice-reasoning">
          {{ truncatedReasoning }}
        </div>
      </div>
      
      <div class="advice-right">
        <span class="advice-time">{{ formatTime(advice.timestamp) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraderStore } from '@/store/app'
import { Bot, ArrowUp, ArrowDown, Pause, X } from 'lucide-vue-next'

const store = useTraderStore()
const { aiAdvice: advice, gameParams, bidData, askData, activeOrders } = storeToRefs(store)

// Use exact same logic as PlaceOrder for price generation
const step = computed(() => gameParams.value.step || 1)
const orderBookLevels = computed(() => gameParams.value.order_book_levels || 5)

const hasBidData = computed(() => bidData.value && bidData.value.length > 0)
const hasAskData = computed(() => askData.value && askData.value.length > 0)

const bestBid = computed(() =>
  hasBidData.value ? Math.max(...bidData.value.map((bid) => bid.x)) : null
)
const bestAsk = computed(() =>
  hasAskData.value ? Math.min(...askData.value.map((ask) => ask.x)) : null
)

// Generate exact same price arrays as PlaceOrder
const buyPrices = computed(() => {
  if (bestAsk.value === null || !orderBookLevels.value) {
    if (bestBid.value === null) return []
    return Array.from(
      { length: orderBookLevels.value },
      (_, i) => bestBid.value + step.value * 1 - step.value * i
    )
  } else {
    return Array.from({ length: orderBookLevels.value }, (_, i) => bestAsk.value - step.value * i)
  }
})

const sellPrices = computed(() => {
  if (bestBid.value === null || !orderBookLevels.value) {
    if (bestAsk.value === null) return []
    return Array.from(
      { length: orderBookLevels.value },
      (_, i) => bestAsk.value - step.value * 1 + step.value * i
    )
  } else {
    return Array.from({ length: orderBookLevels.value }, (_, i) => bestBid.value + step.value * i)
  }
})

// Clamp price to available prices in PlaceOrder panel
const clampedPrice = computed(() => {
  if (!advice.value?.price) return null
  
  const advicePrice = advice.value.price
  const goal = store.traderAttributes?.goal || 0
  
  const availablePrices = goal > 0 ? buyPrices.value : sellPrices.value
  
  if (availablePrices.length === 0) return advicePrice
  
  let closest = availablePrices[0]
  let minDiff = Math.abs(advicePrice - closest)
  
  for (const price of availablePrices) {
    const diff = Math.abs(advicePrice - price)
    if (diff < minDiff) {
      minDiff = diff
      closest = price
    }
  }
  
  return closest
})

const actionClass = computed(() => {
  if (!advice.value) return ''
  switch (advice.value.action) {
    case 'place_order':
      return store.traderAttributes?.goal > 0 ? 'buy-action' : 'sell-action'
    case 'hold':
      return 'hold-action'
    case 'cancel_order':
      return 'cancel-action'
    default:
      return ''
  }
})

const actionIcon = computed(() => {
  if (!advice.value) return Pause
  switch (advice.value.action) {
    case 'place_order':
      return store.traderAttributes?.goal > 0 ? ArrowUp : ArrowDown
    case 'hold':
      return Pause
    case 'cancel_order':
      return X
    default:
      return Pause
  }
})

const actionText = computed(() => {
  if (!advice.value) return ''
  switch (advice.value.action) {
    case 'place_order':
      const side = store.traderAttributes?.goal > 0 ? 'BUY' : 'SELL'
      return `${side} at ${clampedPrice.value}`
    case 'hold':
      return 'Hold'
    case 'cancel_order':
      const orderId = advice.value.order_id
      if (orderId && activeOrders.value) {
        const order = activeOrders.value.find(o => o.id === orderId)
        if (order) {
          return `Cancel @ ${order.price}`
        }
      }
      return 'Cancel order'
    default:
      return advice.value.action
  }
})

const truncatedReasoning = computed(() => {
  if (!advice.value?.reasoning) return ''
  const text = advice.value.reasoning
  return text.length > 120 ? text.substring(0, 120) + '...' : text
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.ai-advisor-banner {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  min-height: 56px;
}

.waiting-advice {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6b7280;
  font-size: 0.875rem;
  width: 100%;
  justify-content: center;
}

.advisor-icon {
  color: #6366f1;
  flex-shrink: 0;
}

.advisor-icon.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.advice-content {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.advice-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.advice-label {
  font-weight: 600;
  color: #374151;
  font-size: 0.875rem;
}

.advice-center {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.advice-action {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.buy-action {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(29, 78, 216, 0.15) 100%);
  color: #1d4ed8;
  border: 1px solid rgba(37, 99, 235, 0.3);
}

.sell-action {
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.15) 0%, rgba(185, 28, 28, 0.15) 100%);
  color: #b91c1c;
  border: 1px solid rgba(220, 38, 38, 0.3);
}

.hold-action {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.15) 0%, rgba(75, 85, 99, 0.15) 100%);
  color: #4b5563;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.cancel-action {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.15) 100%);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.action-icon {
  flex-shrink: 0;
}

.advice-reasoning {
  font-size: 0.8rem;
  color: #6b7280;
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.advice-right {
  flex-shrink: 0;
}

.advice-time {
  font-size: 0.75rem;
  color: #9ca3af;
}
</style>
