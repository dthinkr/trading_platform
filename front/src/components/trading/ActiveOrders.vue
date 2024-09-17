<template>
  <v-card height="100%" elevation="3" class="my-orders-card">

    <div class="orders-container">
      <div v-if="Object.keys(orderLevels).length === 0" class="no-orders-message">
        No active orders
      </div>
      <div v-else v-for="(level, price) in orderLevels" :key="price" class="order-level" :class="level.type === 1 ? 'bid' : 'ask'">
        <div class="order-header">
          <span class="order-type">{{ level.type === 1 ? 'BUY' : 'SELL' }}</span>
          <div class="price">{{ formatPrice(price) }}</div>
        </div>
        <div class="order-details">
          <div class="amount">
            Amount: {{ level.amount }}
          </div>
          <div class="order-actions">
            <v-btn
              icon
              x-small
              @click="addOrder(level.type, price)"
              color="success"
              class="action-btn"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
            <v-btn
              icon
              x-small
              @click="cancelOrder(level.type, price)"
              color="error"
              class="action-btn"
            >
              <v-icon>mdi-minus</v-icon>
            </v-btn>
          </div>
        </div>
        <v-progress-linear
          :value="level.amount / maxAmount * 100"
          :color="level.type === 1 ? 'success' : 'error'"
          height="4"
          class="amount-progress"
        ></v-progress-linear>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { activeOrders } = storeToRefs(traderStore);

const orderLevels = computed(() => {
  const levels = {};
  activeOrders.value.forEach(order => {
    const price = order.price.toString();
    if (!levels[price]) {
      levels[price] = { type: order.type, amount: 0 };
    }
    levels[price].amount += order.amount;
  });

  console.log('Processed Order Levels:', levels);
  return Object.entries(levels)
    .sort(([priceA], [priceB]) => Number(priceB) - Number(priceA))
    .reduce((acc, [price, level]) => {
      acc[price] = level;
      return acc;
    }, {});
});

const maxAmount = computed(() => {
  return Math.max(...Object.values(orderLevels.value).map(level => level.amount), 1);
});

function formatPrice(price) {
  return Number(price).toFixed(2);
}

function addOrder(type, price) {
  const newOrder = {
    type: type,
    price: Number(price),
    amount: 1
  };
  traderStore.addOrder(newOrder);
}

function cancelOrder(type, price) {
  // Assuming cancelOrder in the store now takes an order object
  const orderToCancel = activeOrders.value.find(order => order.type === type && order.price === Number(price));
  if (orderToCancel) {
    traderStore.cancelOrder(orderToCancel.id);
  }
}
</script>

<style scoped>
.my-orders-card {
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
}

.cardtitle-primary {
  color: black;
  font-weight: bold;
  padding: 12px 16px;
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
}

.order-level {
  background-color: white;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  position: relative;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.order-level:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.order-level.bid {
  border-left: 4px solid #2196F3;
}

.order-level.ask {
  border-left: 4px solid #F44336;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.order-type {
  font-weight: bold;
  text-transform: uppercase;
}

.order-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.price {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.amount {
  font-size: 0.9rem;
  color: #666;
}

.order-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 24px;
  height: 24px;
}

.amount-progress {
  margin-top: 8px;
}

.no-orders-message {
  text-align: center;
  color: #666;
  padding: 20px;
}
</style>