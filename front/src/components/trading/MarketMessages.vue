<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <InformationCircleIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Market Info
      </h3>
    </div>
    <div class="card-body">
      <div v-if="messages.length === 0" class="text-center py-8 text-neutral-500">
        <ChatBubbleLeftIcon class="h-12 w-12 mx-auto mb-2 text-neutral-300" aria-hidden="true" />
        <p>No market messages yet</p>
      </div>
      <div v-else class="space-y-2">
        <div v-for="message in messages" :key="message.id" 
             class="p-3 rounded-lg bg-blue-50 border border-blue-200 text-sm">
          <p class="text-blue-800">{{ message.text }}</p>
          <div class="text-xs text-blue-600 mt-1">
            {{ formatTime(message.timestamp) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { InformationCircleIcon, ChatBubbleLeftIcon } from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'

const tradingStore = useTradingStore()

const messages = computed(() => tradingStore.messages)

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString()
}
</script>

<style scoped>
.market-info-card {
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.market-info-content {
  height: 300px;
  overflow-y: auto;
  padding: 0;
}

.info-title {
  font-size: 12px;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
}

.v-icon.v-icon--size-x-small {
  font-size: 14px;
  margin-left: 4px;
}

/* Custom scrollbar for webkit browsers */
.market-info-content::-webkit-scrollbar {
  width: 8px;
}

.market-info-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.market-info-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.market-info-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>