<template>
  <div class="ai-advisor-panel">
    <div v-if="!advisorEnabled" class="no-advisor">
      <Bot :size="24" class="advisor-icon muted" />
      <span>No AI advisor for this session</span>
    </div>
    
    <div v-else-if="!advice" class="waiting-advice">
      <Bot :size="24" class="advisor-icon pulse" />
      <span>AI advisor is analyzing...</span>
    </div>
    
    <div v-else class="advice-content">
      <div class="advice-header">
        <Bot :size="20" class="advisor-icon" />
        <span class="advice-label">AI Suggestion</span>
        <span class="advice-time">{{ formatTime(advice.timestamp) }}</span>
      </div>
      
      <div class="advice-action" :class="actionClass">
        <component :is="actionIcon" :size="18" class="action-icon" />
        <span class="action-text">{{ actionText }}</span>
      </div>
      
      <div v-if="advice.reasoning" class="advice-reasoning">
        <span class="reasoning-text">{{ advice.reasoning }}</span>
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
const { aiAdvice: advice, advisorEnabled, gameParams, bidData, askData, activeOrders } = storeToRefs(store)

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
  
  // Use buy prices for buyers, sell prices for sellers
  const availablePrices = goal > 0 ? buyPrices.value : sellPrices.value
  
  if (availablePrices.length === 0) return advicePrice
  
  // Find the closest available price
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
      return 'Hold - Wait for better opportunity'
    case 'cancel_order':
      const orderId = advice.value.order_id
      if (orderId && activeOrders.value) {
        const order = activeOrders.value.find(o => o.id === orderId)
        if (order) {
          return `Cancel order at ${order.price}`
        }
      }
      return 'Cancel order'
    default:
      return advice.value.action
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.ai-advisor-panel {
  padding: 16px;
  height: 180px;
  max-height: 180px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.no-advisor,
.waiting-advice {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #6b7280;
  font-size: 0.9rem;
}

.advisor-icon {
  color: #6366f1;
}

.advisor-icon.muted {
  color: #9ca3af;
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
  flex-direction: column;
  gap: 8px;
  flex: 1;
  overflow: hidden;
}

.advice-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.advice-label {
  font-weight: 600;
  color: #374151;
  flex: 1;
}

.advice-time {
  font-size: 0.75rem;
  color: #9ca3af;
}

.advice-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.buy-action {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(29, 78, 216, 0.1) 100%);
  color: #1d4ed8;
  border: 1px solid rgba(37, 99, 235, 0.2);
}

.sell-action {
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.1) 0%, rgba(185, 28, 28, 0.1) 100%);
  color: #b91c1c;
  border: 1px solid rgba(220, 38, 38, 0.2);
}

.hold-action {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1) 0%, rgba(75, 85, 99, 0.1) 100%);
  color: #4b5563;
  border: 1px solid rgba(107, 114, 128, 0.2);
}

.cancel-action {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.action-icon {
  flex-shrink: 0;
}

.advice-details {
  display: flex;
  gap: 8px;
  font-size: 0.875rem;
}

.detail-label {
  color: #6b7280;
}

.detail-value {
  font-weight: 600;
  color: #111827;
}

.advice-reasoning {
  font-size: 0.75rem;
  color: #6b7280;
  font-style: italic;
  padding: 6px 8px;
  background: #f9fafb;
  border-radius: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  line-height: 1.3;
}

.advice-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  color: #9ca3af;
  padding-top: 6px;
  border-top: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.note-icon {
  flex-shrink: 0;
}
</style>
