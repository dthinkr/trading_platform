<template>
  <div class="ai-advisor-panel">
    <div v-if="!hasAdvisor" class="no-advisor">
      <Bot :size="24" class="advisor-icon muted" />
      <span>No AI advisor connected</span>
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
      
      <div v-if="advice.price" class="advice-details">
        <span class="detail-label">Price:</span>
        <span class="detail-value">{{ advice.price }}</span>
      </div>
      
      <div v-if="advice.reasoning" class="advice-reasoning">
        <span class="reasoning-text">{{ advice.reasoning }}</span>
      </div>
      
      <div class="advice-note">
        <Info :size="14" class="note-icon" />
        <span>This is a suggestion only. You decide whether to act.</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTraderStore } from '@/store/app'
import { Bot, ArrowUp, ArrowDown, Pause, X, Info } from 'lucide-vue-next'

const store = useTraderStore()
const { aiAdvice: advice, hasAdvisor } = storeToRefs(store)

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
      return `${side} at ${advice.value.price}`
    case 'hold':
      return 'Hold - Wait for better opportunity'
    case 'cancel_order':
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
  min-height: 120px;
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
  gap: 12px;
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
  padding: 12px 16px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 1rem;
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
  font-size: 0.8rem;
  color: #6b7280;
  font-style: italic;
  padding: 8px;
  background: #f9fafb;
  border-radius: 8px;
}

.advice-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: #9ca3af;
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.note-icon {
  flex-shrink: 0;
}
</style>
