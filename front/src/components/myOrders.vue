<template>
  <v-card height="100%" elevation="3" class="my-orders-card">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-format-list-bulleted</v-icon>
      My Orders
    </v-card-title>
    
    <div class="orders-container">
      <div v-for="(level, price) in orderLevels" :key="price" class="order-level" :class="level.type.toLowerCase()">
        <div class="order-header">
          <span class="order-type">{{ level.type }}</span>
          <div class="price">{{ formatPrice(price) }}</div>
        </div>
        <div class="order-details">
          <div class="amount">
            Active: {{ level.active }}
            Pending: {{ level.pending }}
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
          :value="(level.active + level.pending) / maxAmount * 100"
          :color="level.type === 'BID' ? 'success' : 'error'"
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
const { placedOrders } = storeToRefs(traderStore);

const orderLevels = computed(() => {
  const levels = {};
  placedOrders.value.forEach(order => {
    if (!levels[order.price]) {
      levels[order.price] = { type: order.order_type, active: 0, pending: 0 };
    }
    if (order.status === 'active') {
      levels[order.price].active += order.amount;
    } else if (order.status === 'pending') {
      levels[order.price].pending += order.amount;
    }
  });
  return Object.entries(levels)
    .sort(([priceA], [priceB]) => Number(priceB) - Number(priceA))
    .reduce((acc, [price, level]) => {
      acc[price] = level;
      return acc;
    }, {});
});

const maxAmount = computed(() => {
  return Math.max(...Object.values(orderLevels.value).map(level => level.active + level.pending), 1);
});

function formatPrice(price) {
  return Math.round(Number(price)).toFixed(0);
}

function addOrder(type, price) {
  const newOrder = {
    id: Date.now().toString(),
    order_type: type, // Keep as 'BID' or 'ASK' for frontend use
    price: Number(price),
    amount: 1,
    status: 'pending'
  };
  traderStore.addOrder(newOrder);
}

function cancelOrder(type, price) {
  const orderToCancel = placedOrders.value.find(order => 
    order.order_type === type && 
    order.price === Number(price) &&
    order.status === 'active'
  );
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
</style>