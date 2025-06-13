<script setup>
import { computed } from "vue";
import { useTradingStore } from "@/stores/trading";
import { useAuthStore } from "@/stores/auth";
import { storeToRefs } from "pinia";
import { ClockIcon, DocumentIcon } from '@heroicons/vue/24/outline'

const tradingStore = useTradingStore();
const authStore = useAuthStore();
const { filledOrders, recentTransactions } = storeToRefs(tradingStore);
const { traderId } = storeToRefs(authStore);

// Use the filled orders from the trading store directly
const orders = computed(() => {
  return filledOrders.value.map(order => ({
    id: order.id,
    type: order.type === 'BID' ? 'BUY' : 'SELL',
    price: order.price,
    quantity: order.quantity,
    timestamp: order.timestamp
  }));
});

// Helper functions
const formatPrice = (price) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(price);
};

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <ClockIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Order History
      </h3>
    </div>
    <div class="card-body">
      <div v-if="orders.length === 0" class="text-center py-8 text-neutral-500">
        <DocumentIcon class="h-12 w-12 mx-auto mb-2 text-neutral-300" aria-hidden="true" />
        <p>No order history yet</p>
              </div>
      <div v-else class="space-y-2">
        <div v-for="order in orders" :key="order.id" 
             class="p-3 rounded-lg border border-neutral-200 text-sm">
          <div class="flex justify-between items-center">
            <span :class="order.type === 'BUY' ? 'text-green-600' : 'text-red-600'" class="font-medium">
              {{ order.type }}
            </span>
            <span class="font-mono">{{ formatPrice(order.price) }}</span>
              </div>
          <div class="text-xs text-neutral-500 mt-1">
            {{ formatTime(order.timestamp) }}
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-history-card {
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.trading-summary {
  background-color: #fafafa;
  padding: 6px;
}

.vwap-display, .count-display {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 0.9rem;
  white-space: nowrap;
  position: relative;
}

.label {
  position: absolute;
  left: 0;
  font-size: 0.7rem;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
}

/* .count-display {
  margin-top: 4px;
  font-size: 0.8rem;
} */

.vwap-item, .count-item {
  font-weight: 500;
}

/* .count-divider {
  color: #999;
} */

.vwap-item.buy, .count-item.buy {
  color: #1976D2;
}

.vwap-item.sell, .count-item.sell {
  color: #D32F2F;
}

.order-history-container {
  height: 200px;
  overflow-y: auto;
}

.order-columns {
  display: flex;
  gap: 16px;
}

.order-column {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.order-item {
  background-color: white;
  border-radius: 6px;
  padding: 2px 10px;
  margin-bottom: 4px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease;
}

.order-item:hover {
  transform: translateY(-2px);
}

.order-item.bid {
  border-left: 3px solid #2196F3;
  background-color: #f3f8fe;
}

.order-item.ask {
  border-left: 3px solid #F44336;
  background-color: #fef3f3;
}

.price-amount {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}

.price {
  font-size: 13px;
  font-weight: 600;
}

.amount {
  font-size: 11px;
  font-weight: 500;
  color: #666;
}

.time {
  font-size: 10px;
  color: #888;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.no-orders-message {
  text-align: center;
  color: #9e9e9e;
  font-size: 14px;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.order-change-enter-active,
.order-change-leave-active {
  transition: all 0.3s ease;
}

.order-change-enter-from,
.order-change-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* Scrollbar styles */
.order-history-container::-webkit-scrollbar {
  width: 4px;
}

.order-history-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.order-history-container::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 2px;
}

.order-history-container::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
