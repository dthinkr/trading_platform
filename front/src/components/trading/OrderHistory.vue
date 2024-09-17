<template>
  <v-card height="100%" elevation="3" class="message-board">
    <v-card-title class="cardtitle">
      <v-icon left color="white">mdi-history</v-icon>
      Order History
    </v-card-title>
    <v-card-text class="message-container" ref="messageContainer">
      <v-container v-if="groupedOrders.bids.length || groupedOrders.asks.length">
        <div class="order-columns">
          <div class="order-column">
            <h3 class="column-title">Buy Orders</h3>
            <div v-for="order in groupedOrders.bids" :key="order.price" class="order-item bid">
              <span class="price">{{ formatPrice(order.price) }}</span>
              <span class="amount">{{ order.amount }}</span>
            </div>
          </div>
          <div class="order-column">
            <h3 class="column-title">Sell Orders</h3>
            <div v-for="order in groupedOrders.asks" :key="order.price" class="order-item ask">
              <span class="price">{{ formatPrice(order.price) }}</span>
              <span class="amount">{{ order.amount }}</span>
            </div>
          </div>
        </div>
      </v-container>
      <div v-else class="no-orders-message">
        No executed orders yet.
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { executedOrders, recentTransactions } = storeToRefs(traderStore);

const filledOrders = computed(() => {
  // Combine executedOrders and relevant recentTransactions
  const relevantTransactions = recentTransactions.value.filter(t => t.isRelevantToTrader);
  return [...executedOrders.value, ...relevantTransactions];
});

const groupedOrders = computed(() => {
  const bids = {};
  const asks = {};

  filledOrders.value.forEach(order => {
    const isBid = order.type === 1 || order.type === 'BID' || order.type === 'BUY' || order.bid_order_id?.startsWith(traderStore.traderUuid);
    const group = isBid ? bids : asks;
    const price = order.price || order.transaction_price;
    const amount = order.amount || 1; // Assuming 1 if not specified

    if (!group[price]) {
      group[price] = { price: price, amount: 0 };
    }
    group[price].amount += amount;
  });

  return {
    bids: Object.values(bids).sort((a, b) => b.price - a.price),
    asks: Object.values(asks).sort((a, b) => a.price - b.price)
  };
});

const formatPrice = (price) => {
  return `$${Number(price).toFixed(2)}`;
};
</script>

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
  justify-content: space-between;
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

.price {
  font-weight: bold;
}

.amount {
  color: #666;
}

.no-orders-message {
  text-align: center;
  color: #666;
  padding: 20px;
}
</style>