<template>
  <v-card height="100%" elevation="3" class="message-board">
    <v-card-title class="cardtitle">
      <v-icon left color="white">mdi-history</v-icon>
      Order History
    </v-card-title>
    <v-card-text class="message-container" ref="messageContainer">
      <v-container v-if="executedOrders.length">
        <TransitionGroup name="message" tag="div" class="messages-container">
          <div 
            class="message"
            v-for="order in executedOrders" 
            :key="order.id" 
            :ref="setRef"
          >
            <v-icon left small :color="getOrderColor(order)" class="mr-2">mdi-check-circle</v-icon>
            {{ formatOrderMessage(order) }}
          </div>
        </TransitionGroup>
      </v-container>
      <div v-else class="no-orders-message">
        No executed orders yet.
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { executedOrders } = storeToRefs(traderStore);

const messageRefs = ref([]);

const setRef = (el) => {
  if (el) {
    messageRefs.value.push(el);
  }
};

const scrollToLastMessage = () => {
  const lastMessageElement = messageRefs.value.at(-1);
  if (lastMessageElement) {
    lastMessageElement.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

const getOrderColor = (order) => {
  return order.order_type === 'BID' ? "success" : "error";
};

const formatOrderMessage = (order) => {
  const action = order.order_type === 'BID' ? 'Buy' : 'Sell';
  return `${action} order executed: ${order.amount} @ $${order.price}`;
};

onMounted(() => {
  watch(executedOrders, async () => {
    await nextTick();
    scrollToLastMessage();
  });
});
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

.messages-container {
  padding: 8px;
}

.message {
  background-color: white;
  border-left: 4px solid #3498db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  padding: 12px 16px;
  margin-bottom: 12px;
  word-wrap: break-word;
  font-size: 0.9rem;
  line-height: 1.4;
  transition: all 0.3s ease;
}

.message:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.message-enter-active, .message-leave-active {
  transition: all 0.5s ease;
}

.message-enter-from, .message-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.message-enter-to, .message-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.no-orders-message {
  text-align: center;
  color: #666;
  padding: 20px;
}
</style>