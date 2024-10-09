<script setup>
import { computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { executedOrders, recentTransactions, traderUuid } = storeToRefs(traderStore);

const filledOrders = computed(() => {
  // Combine executedOrders and relevant recentTransactions
  const relevantTransactions = recentTransactions.value.filter(t => t.isRelevantToTrader);
  return [...executedOrders.value, ...relevantTransactions];
});

const groupedOrders = computed(() => {
  const bids = {};
  const asks = {};

  filledOrders.value.forEach(order => {
    const isBid = order.type === 1 || order.type === 'BID' || order.type === 'BUY' || order.bid_order_id?.startsWith(traderUuid.value);
    const isAsk = order.type === 2 || order.type === 'ASK' || order.type === 'SELL' || order.ask_order_id?.startsWith(traderUuid.value);
    
    // Only process the order if it's on the side the trader placed
    if (!(isBid || isAsk)) return;

    const group = isBid ? bids : asks;
    const price = order.price || order.transaction_price;
    const amount = order.amount || order.transaction_amount;
    const timestamp = new Date(order.timestamp || order.transaction_time).getTime();

    if (!group[price]) {
      group[price] = { price: price, amount: amount, latestTime: timestamp };
    } else {
      group[price].amount += amount;
      if (timestamp > group[price].latestTime) {
        group[price].latestTime = timestamp;
      }
    }
  });

  const sortByTimeDesc = (a, b) => b.latestTime - a.latestTime;

  return {
    bids: Object.values(bids).sort(sortByTimeDesc),
    asks: Object.values(asks).sort(sortByTimeDesc)
  };
});

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};
</script>

<template>
  <v-card height="100%" elevation="3" class="order-history-card">
    <div class="order-history-container">
      <div v-if="groupedOrders.bids.length || groupedOrders.asks.length" class="order-columns">
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div v-for="order in groupedOrders.bids" :key="order.price" class="order-item bid">
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }}</span>
              </div>
              <div class="time">{{ formatTime(order.latestTime) }}</div>
            </div>
          </TransitionGroup>
        </div>
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div v-for="order in groupedOrders.asks" :key="order.price" class="order-item ask">
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }}</span>
              </div>
              <div class="time">{{ formatTime(order.latestTime) }}</div>
            </div>
          </TransitionGroup>
        </div>
      </div>
      <div v-else class="no-orders-message">
        No executed orders yet.
      </div>
    </div>
  </v-card>
</template>

<style scoped>
.order-history-card {
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.order-history-container {
  height: 300px;
  overflow-y: auto;
  padding: 16px;
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
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
}

.order-item.bid {
  border-left: 3px solid #2196F3;
}

.order-item.ask {
  border-left: 3px solid #F44336;
}

.price-amount {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 4px;
}

.price {
  font-size: 14px;
  font-weight: 600;
}

.amount {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.time {
  font-size: 10px;
  color: #888;
  align-self: flex-end;
}

.no-orders-message {
  text-align: center;
  color: #666;
  font-size: 14px;
  padding: 20px;
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