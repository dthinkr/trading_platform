<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <ListBulletIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Active Orders
      </h3>
    </div>
    <div class="card-body">
      <div v-if="activeOrders.length === 0" class="text-center py-8 text-neutral-500">
        <ClipboardDocumentListIcon class="h-12 w-12 mx-auto mb-2 text-neutral-300" aria-hidden="true" />
        <p>No active orders</p>
      </div>
      <div v-else class="space-y-2">
        <div v-for="order in activeOrders" :key="order.id" 
             class="p-3 rounded-lg border border-neutral-200 text-sm">
          <div class="flex justify-between items-center">
            <span :class="order.type === 'BUY' ? 'text-green-600' : 'text-red-600'" class="font-medium">
              {{ order.type }}
            </span>
            <span class="font-mono">{{ formatPrice(order.price) }}</span>
            <button @click="cancelOrder(order.id)" 
                    class="text-red-600 hover:text-red-800 text-xs">
              Cancel
            </button>
          </div>
          <div class="text-xs text-neutral-500 mt-1">
            {{ order.quantity }} shares
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ListBulletIcon, ClipboardDocumentListIcon } from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'

const tradingStore = useTradingStore()

const activeOrders = computed(() => tradingStore.activeOrders)

function formatPrice(price) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0
  }).format(price)
}

async function cancelOrder(orderId) {
  try {
    await tradingStore.cancelOrder(orderId)
  } catch (error) {
    console.error('Failed to cancel order:', error)
  }
}
</script>
