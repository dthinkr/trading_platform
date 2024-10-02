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
  <v-card height="100%" elevation="3" class="message-board">
    <v-card-text class="message-container" ref="messageContainer">
      <v-container v-if="groupedOrders.bids.length || groupedOrders.asks.length">
        <div class="order-columns">
          <div class="order-column">
            <h3 class="column-title">Buy Orders</h3>
            <TransitionGroup name="order-change">
              <div v-for="order in groupedOrders.bids" :key="order.price" class="order-item bid">
                <div class="order-details">
                  <div class="price-amount">
                    <span class="price">${{ order.price }}</span>
                    <span class="amount">{{ order.amount }}</span>
                  </div>
                  <div class="time">{{ formatTime(order.latestTime) }}</div>
                </div>
              </div>
            </TransitionGroup>
          </div>
          <div class="order-column">
            <h3 class="column-title">Sell Orders</h3>
            <TransitionGroup name="order-change">
              <div v-for="order in groupedOrders.asks" :key="order.price" class="order-item ask">
                <div class="order-details">
                  <div class="price-amount">
                    <span class="price">${{ order.price }}</span>
                    <span class="amount">{{ order.amount }}</span>
                  </div>
                  <div class="time">{{ formatTime(order.latestTime) }}</div>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </v-container>
      <div v-else class="no-orders-message">
        No executed orders yet.
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.message-board {
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
}

.cardtitle {
  font-size: 18px;
  font-weight: bold;
  background: linear-gradient(to right, #2c3e50, #34495e);
  color: white;
  padding: 12px 16px;
}

.message-container {
  height: 300px;
  overflow-y: auto;
  padding: 0;
}

.order-columns {
  display: flex;
  justify-content: space-between;
}

.order-column {
  width: 48%;
}

.column-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
  text-align: center;
}

.order-item {
  display: flex;
  justify-content: center;
  padding: 8px;
  margin-bottom: 5px;
  border-radius: 4px;
  font-size: 0.9rem;
}

.order-item.bid {
  background-color: rgba(33, 150, 243, 0.1); /* Light blue background */
  border-left: 3px solid #2196F3; /* Blue border */
}

.order-item.ask {
  background-color: rgba(244, 67, 54, 0.1); /* Light red background */
  border-left: 3px solid #F44336; /* Red border */
}

.order-details {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.price-amount {
  display: flex;
  gap: 10px;
  margin-bottom: 4px;
}

.price {
  font-weight: bold;
}

.amount {
  font-weight: bold;
}

.time {
  font-size: 0.8rem;
  color: #555;
}

.no-orders-message {
  text-align: center;
  color: #666;
  padding: 20px;
}

.order-change-enter-active,
.order-change-leave-active {
  transition: all 0.5s ease;
}

.order-change-enter-from,
.order-change-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

.order-change-enter-to,
.order-change-leave-from {
  opacity: 1;
  transform: translateY(0);
}

@keyframes highlight {
  0% {
    background-color: yellow;
  }
  100% {
    background-color: transparent;
  }
}

.order-item {
  animation: highlight 1s ease-out;
}
</style>