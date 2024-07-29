<template>
  <v-card height="100%" elevation="3" class="my-orders-card">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-format-list-bulleted</v-icon>
      My Orders
    </v-card-title>
    
    <div class="orders-container">
      <div v-for="(item, index) in paginatedOrders" :key="index" class="order-item" :class="item.order_type.toLowerCase()">
        <div class="order-header">
          <span class="order-type">{{ item.order_type }}</span>
          <div class="price">{{ formatNumber(item.price) }}</div>
        </div>
        <div class="order-details">
          <div class="amount">Amount: {{ item.totalAmount }}</div>
          <div class="order-actions">
            <v-btn
              icon
              x-small
              @click="addOrder(item)"
              color="success"
              class="action-btn"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
            <v-btn
              icon
              x-small
              @click="removeOrder(item)"
              color="error"
              class="action-btn"
            >
              <v-icon>mdi-minus</v-icon>
            </v-btn>
          </div>
        </div>
        <v-progress-linear
          :value="(item.totalAmount / maxAmount) * 100"
          :color="item.order_type === 'BID' ? 'success' : 'error'"
          height="4"
          class="amount-progress"
        ></v-progress-linear>
      </div>
    </div>
    <div class="pagination">
      <v-btn
        icon
        small
        :disabled="currentPage === 1"
        @click="currentPage--"
      >
        <v-icon>mdi-chevron-left</v-icon>
      </v-btn>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <v-btn
        icon
        small
        :disabled="currentPage === totalPages"
        @click="currentPage++"
      >
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useFormatNumber } from '@/composables/utils';

const { formatNumber } = useFormatNumber();
const traderStore = useTraderStore();
const { myOrders } = storeToRefs(traderStore);
const { sendMessage } = traderStore;

const currentPage = ref(1);
const itemsPerPage = 4; // 2 rows, 2 items per row

const localOrders = ref([]);

const combinedOrders = computed(() => {
  const orderMap = new Map();
  localOrders.value.forEach(order => {
    const key = `${order.order_type}-${order.price}`;
    if (!orderMap.has(key)) {
      orderMap.set(key, { ...order, totalAmount: 0 });
    }
    orderMap.get(key).totalAmount += order.amount;
  });
  return Array.from(orderMap.values());
});

const sortedOrders = computed(() => {
  return [...combinedOrders.value].sort((a, b) => b.price - a.price);
});

const maxAmount = computed(() => {
  return Math.max(...sortedOrders.value.map(order => order.totalAmount));
});

const totalPages = computed(() => Math.ceil(sortedOrders.value.length / itemsPerPage));

const paginatedOrders = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return sortedOrders.value.slice(start, end);
});

const addOrder = (item) => {
  const newOrder = {
    id: Date.now().toString(), // Temporary ID
    order_type: item.order_type,
    price: item.price,
    amount: 1,
    status: 'active'
  };
  localOrders.value.push(newOrder);
  sendMessage("add_order", { type: item.order_type === 'ASK' ? -1 : 1, price: item.price, amount: 1 });
};

const removeOrder = (item) => {
  const orderToRemove = localOrders.value.find(order => 
    order.order_type === item.order_type && 
    order.price === item.price &&
    order.status === 'active'
  );
  if (orderToRemove) {
    orderToRemove.status = 'cancelled';
    sendMessage("cancel_order", { id: orderToRemove.id });
  }
};

// Initialize localOrders with myOrders
watch(myOrders, (newOrders) => {
  localOrders.value = JSON.parse(JSON.stringify(newOrders));
}, { immediate: true, deep: true });

// Sync localOrders with server responses
const syncOrders = (serverOrders) => {
  localOrders.value = serverOrders.map(order => ({
    ...order,
    amount: order.amount || 1 // Ensure amount is at least 1
  }));
};

// Watch for changes in myOrders (server updates)
watch(myOrders, syncOrders, { deep: true });

// Expose syncOrders to parent component if needed
defineExpose({ syncOrders });
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
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.order-item {
  background-color: white;
  border-radius: 8px;
  padding: 12px;
  position: relative;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.order-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.order-item.bid {
  border-left: 4px solid #2196F3;
}

.order-item.ask {
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

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
}

.page-info {
  margin: 0 12px;
  font-size: 0.9rem;
  color: #666;
}
</style>