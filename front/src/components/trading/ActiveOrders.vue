<template>
  <v-card height="100%" elevation="3" class="my-orders-card">
    <div class="orders-container">
      <div v-if="Object.keys(sortedOrderLevels).length === 0" class="no-orders-message">
        No active orders
      </div>
      <div v-else class="orders-columns">
        <div class="orders-column bid-column">
          <div class="order-levels-container">
            <div v-for="[price, level] in sortedOrderLevels.buy" :key="price" class="order-level bid">
              <div class="order-header">
                <span class="order-type">BUY</span>
                <div class="price">{{ formatPrice(price) }}</div>
              </div>
              <div class="order-details">
                <div class="amount">Amount: {{ level.amount }}</div>
                <div class="order-actions">
                  <v-btn
                    icon
                    x-small
                    @click="addOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="success"
                    class="action-btn"
                  >
                    <v-icon small>mdi-plus</v-icon>
                  </v-btn>
                  <v-btn
                    icon
                    x-small
                    @click="cancelOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="error"
                    class="action-btn"
                  >
                    <v-icon small>mdi-minus</v-icon>
                  </v-btn>
                </div>
              </div>
              <v-progress-linear :value="level.amount / maxAmount * 100" color="success" height="2" class="amount-progress"></v-progress-linear>
            </div>
          </div>
        </div>
        <div class="orders-column ask-column">
          <div class="order-levels-container">
            <div v-for="[price, level] in sortedOrderLevels.sell" :key="price" class="order-level ask">
              <div class="order-header">
                <span class="order-type">SELL</span>
                <div class="price">{{ formatPrice(price) }}</div>
              </div>
              <div class="order-details">
                <div class="amount">Amount: {{ level.amount }}</div>
                <div class="order-actions">
                  <v-btn
                    icon
                    x-small
                    @click="addOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="success"
                    class="action-btn"
                  >
                    <v-icon small>mdi-plus</v-icon>
                  </v-btn>
                  <v-btn
                    icon
                    x-small
                    @click="cancelOrder(level.type, price)"
                    :disabled="isGoalAchieved"
                    color="error"
                    class="action-btn"
                  >
                    <v-icon small>mdi-minus</v-icon>
                  </v-btn>
                </div>
              </div>
              <v-progress-linear :value="level.amount / maxAmount * 100" color="error" height="2" class="amount-progress"></v-progress-linear>
            </div>
          </div>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const props = defineProps({
  isGoalAchieved: {
    type: Boolean,
    default: false
  }
});

const traderStore = useTraderStore();
const { activeOrders } = storeToRefs(traderStore);

const sortedOrderLevels = computed(() => {
  const levels = { buy: {}, sell: {} };
  activeOrders.value.forEach(order => {
    const type = order.order_type === 1 ? 'buy' : 'sell';
    const price = order.price.toString();
    if (!levels[type][price]) {
      levels[type][price] = { type: order.order_type, amount: 0 };
    }
    levels[type][price].amount += order.amount;
  });

  return {
    buy: Object.entries(levels.buy).sort(([a], [b]) => Number(b) - Number(a)),
    sell: Object.entries(levels.sell).sort(([a], [b]) => Number(a) - Number(b))
  };
});

const maxAmount = computed(() => {
  const allAmounts = [
    ...Object.values(sortedOrderLevels.value.buy).map(([, level]) => level.amount),
    ...Object.values(sortedOrderLevels.value.sell).map(([, level]) => level.amount)
  ];
  return Math.max(...allAmounts, 1);
});

function formatPrice(price) {
  return Math.round(price).toString(); // Changed to round the price
}

function addOrder(type, price) {
  if (!props.isGoalAchieved) {
    traderStore.addOrder({ order_type: type, price: Number(price), amount: 1 });
  }
}

function cancelOrder(type, price) {
  if (!props.isGoalAchieved) {
    const orderToCancel = activeOrders.value.find(order => order.order_type === type && order.price === Number(price));
    if (orderToCancel) {
      traderStore.cancelOrder(orderToCancel.id);
    }
  }
}
</script>

<style scoped>
.my-orders-card {
  display: flex;
  flex-direction: column;
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.orders-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
}

.orders-columns {
  display: flex;
  gap: 16px;
}

.orders-column {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.order-level {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.order-type {
  font-weight: 500;
  text-transform: uppercase;
  font-size: 11px;
}

.price {
  font-size: 14px;
  font-weight: 600;
}

.order-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.amount {
  font-size: 12px;
}

.order-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 20px;
  height: 20px;
}

.amount-progress {
  margin-top: 4px;
}

.no-orders-message {
  text-align: center;
  color: #666;
  font-size: 14px;
  padding: 20px;
}

.order-levels-container {
  max-height: 300px;
  overflow-y: auto;
  padding-right: 8px;
}

/* Scrollbar styles */
.order-levels-container::-webkit-scrollbar {
  width: 4px;
}

.order-levels-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.order-levels-container::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 2px;
}

.order-levels-container::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>