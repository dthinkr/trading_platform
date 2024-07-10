<template>
  <v-card height="100%" elevation="3" class="message-board">
    <v-card-title class="cardtitle">
      <v-icon left color="white">mdi-bell-outline</v-icon>
      Market Updates
    </v-card-title>
    <v-card-text class="message-container" ref="messageContainer">
      <v-container>
        <TransitionGroup name="message" tag="div" class="messages-container">
          <div 
            class="message"
            v-for="(message, index) in messages" 
            :key="index" 
            :ref="setRef" 
            :id="`message_${index}`"
          >
            <v-icon left small :color="getMessageColor(message)" class="mr-2">{{ getMessageIcon(message) }}</v-icon>
            {{ message }}
          </div>
        </TransitionGroup>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";

const tradingMessages = [
  "Your buy order for AAPL has been executed.",
  "Market alert: BTC has dropped by 5% in the last hour.",
  "Reminder: Your portfolio review is due next week.",
  "Trade successful: 100 shares of TSLA sold at $720.00.",
  "Market update: NASDAQ has risen by 0.5% today.",
  "Funds settled: $1,500.00 has been deposited into your account.",
  "Order placed: Buy order for 50 shares of AMZN at $3,100.00.",
  "Warning: Your margin balance is below 20%.",
  "Earnings report: MSFT beats Q3 expectations, shares jump.",
  "Dividend received: $250.00 from KO.",
  "New research report available: Analysis on the recent trends in the EV market.",
  "Price alert: Gold has reached a new 6-month high.",
  "Your limit order to sell 200 shares of NFLX at $550.00 has been placed.",
  "Portfolio update: Your investments have gained 2.5% in value this month.",
  "Reminder: Check out the latest investment strategies on our blog.",
  "Dividend announcement: JNJ has declared a $1.05 per share dividend.",
  "Economic update: The Federal Reserve hints at possible rate hikes next quarter.",
  "Your watchlist update: AMD stock has increased by over 10% this week.",
  "Security notice: Remember to update your password regularly to protect your account.",
  "System maintenance: The platform will be temporarily unavailable from 2 AM to 4 AM this Saturday."
];

const messages = ref([]);
const messageRefs = ref([]);

const setRef = (el) => {
  if (el) {
    messageRefs.value.push(el);
  }
};

const addMessage = async () => {
  const randomMessage = tradingMessages[Math.floor(Math.random() * tradingMessages.length)];
  messages.value.push(randomMessage);
  await nextTick();
  scrollToLastMessage();
};

const scrollToLastMessage = () => {
  const lastMessageElement = messageRefs.value.at(-1);
  if (lastMessageElement) {
    lastMessageElement.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

const getMessageColor = (message) => {
  if (message.includes("alert") || message.includes("Warning")) return "error";
  if (message.includes("successful") || message.includes("executed")) return "success";
  return "primary";
};

const getMessageIcon = (message) => {
  if (message.includes("alert") || message.includes("Warning")) return "mdi-alert-circle-outline";
  if (message.includes("successful") || message.includes("executed")) return "mdi-check-circle-outline";
  return "mdi-information-outline";
};

onMounted(() => {
  const n = 4; // Number of seconds between messages
  setInterval(addMessage, n * 1000); 
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
</style>