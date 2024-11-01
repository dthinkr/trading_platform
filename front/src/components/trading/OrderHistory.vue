<script setup>
import { computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { executedOrders, recentTransactions, traderUuid, shares } = storeToRefs(traderStore);

const filledOrders = computed(() => {
  // Filter transactions to only include those where the current trader was involved
  const relevantTransactions = recentTransactions.value.filter(t => {
    const isBidTrader = t.bid_trader_id === traderUuid.value;
    const isAskTrader = t.ask_trader_id === traderUuid.value;
    return isBidTrader || isAskTrader;
  });

  // Get all order IDs that appear in transactions as either order_id or matched_order_id
  const transactionOrderIds = new Set(
    relevantTransactions.flatMap(t => [t.order_id, t.matched_order_id, t.bid_order_id, t.ask_order_id]
      .filter(Boolean))
  );

  // Filter executed orders to ensure they belong to the current trader
  // and exclude orders that appear in any transaction order IDs
  const relevantExecutedOrders = executedOrders.value.filter(order => 
    order.trader_id === traderUuid.value && !transactionOrderIds.has(order.id)
  );

  // Combine and remove duplicates
  const allOrders = [...relevantExecutedOrders, ...relevantTransactions];
  return Array.from(new Map(
    allOrders.map(order => [order.id || order.timestamp, order])
  ).values());
});

const groupedOrders = computed(() => {
  const bids = {};
  const asks = {};

  filledOrders.value.forEach(order => {
    // Determine if this is a bid or ask for the current trader
    const isBid = (order.bid_trader_id === traderUuid.value) || 
                 (order.trader_id === traderUuid.value && 
                  ['BUY', 'BID', 1].includes(order.type || order.order_type));
                  
    const isAsk = (order.ask_trader_id === traderUuid.value) || 
                 (order.trader_id === traderUuid.value && 
                  ['SELL', 'ASK', -1].includes(order.type || order.order_type));

    // Skip if not the current trader's order
    if (!isBid && !isAsk) return;

    const group = isBid ? bids : asks;
    const price = order.price || order.transaction_price;
    const amount = order.amount || 1;
    const timestamp = new Date(order.timestamp || order.transaction_time).getTime();

    if (!group[price]) {
      group[price] = { 
        price, 
        amount, 
        latestTime: timestamp
      };
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

const tradingSummary = computed(() => {
  let buyCount = 0;
  let sellCount = 0;
  let buyVolume = 0;
  let sellVolume = 0;
  let buyValue = 0;
  let sellValue = 0;

  filledOrders.value.forEach(order => {
    const isBid = (order.bid_trader_id === traderUuid.value) || 
                 (order.trader_id === traderUuid.value && 
                  ['BUY', 'BID', 1].includes(order.type || order.order_type));

    const price = order.price || order.transaction_price;
    const amount = order.amount || 1;

    if (isBid) {
      buyCount++;
      buyVolume += amount;
      buyValue += price * amount;
    } else {
      sellCount++;
      sellVolume += amount;
      sellValue += price * amount;
    }
  });

  return {
    buyCount,
    sellCount,
    buyVWAP: buyVolume > 0 ? (buyValue / buyVolume).toFixed(2) : 0,
    sellVWAP: sellVolume > 0 ? (sellValue / sellVolume).toFixed(2) : 0,
    netPosition: shares.value
  };
});

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};
</script>

<template>
  <v-card height="100%" elevation="3" class="order-history-card">
    <div class="trading-summary pa-3">
      <div class="position-wrapper mb-3">
        <v-chip 
          :color="tradingSummary.netPosition >= 0 ? 'success' : 'error'"
          class="position-chip"
          elevation="2"
        >
          <v-icon left size="18">
            {{ tradingSummary.netPosition >= 0 ? 'mdi-trending-up' : 'mdi-trending-down' }}
          </v-icon>
          <span class="font-weight-medium">
            Position: {{ tradingSummary.netPosition }}
          </span>
        </v-chip>
      </div>
      
      <div class="summary-cards d-flex justify-space-between">
        <div class="summary-card buy elevation-1">
          <div class="card-header blue lighten-5 pa-2">
            <v-icon color="blue darken-2" size="20" class="mr-1">mdi-arrow-up-bold</v-icon>
            <span class="text-subtitle-2 blue--text text--darken-2 font-weight-bold">Buy Trades</span>
          </div>
          <div class="card-content pa-3">
            <div class="stat-row">
              <span class="stat-label">Count:</span>
              <span class="stat-value">{{ tradingSummary.buyCount }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">VWAP:</span>
              <span class="stat-value">{{ tradingSummary.buyVWAP }}</span>
            </div>
          </div>
        </div>
        <div class="summary-card sell elevation-1">
          <div class="card-header red lighten-5 pa-2">
            <v-icon color="red darken-2" size="20" class="mr-1">mdi-arrow-down-bold</v-icon>
            <span class="text-subtitle-2 red--text text--darken-2 font-weight-bold">Sell Trades</span>
          </div>
          <div class="card-content pa-3">
            <div class="stat-row">
              <span class="stat-label">Count:</span>
              <span class="stat-value">{{ tradingSummary.sellCount }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">VWAP:</span>
              <span class="stat-value">{{ tradingSummary.sellVWAP }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <v-divider></v-divider>

    <div class="order-history-container px-4">
      <div v-if="groupedOrders.bids.length || groupedOrders.asks.length" class="order-columns">
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div v-for="order in groupedOrders.bids" :key="order.price" 
                 class="order-item bid elevation-1">
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }} shares</span>
              </div>
              <div class="time">
                <v-icon size="12" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatTime(order.latestTime) }}
              </div>
            </div>
          </TransitionGroup>
        </div>
        <div class="order-column">
          <TransitionGroup name="order-change">
            <div v-for="order in groupedOrders.asks" :key="order.price" 
                 class="order-item ask elevation-1">
              <div class="price-amount">
                <span class="price">{{ Math.round(order.price) }}</span>
                <span class="amount">{{ order.amount }} shares</span>
              </div>
              <div class="time">
                <v-icon size="12" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatTime(order.latestTime) }}
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>
      <div v-else class="no-orders-message">
        <v-icon color="grey" size="40" class="mb-2">mdi-clipboard-text-outline</v-icon>
        <div>No executed trades yet</div>
      </div>
    </div>
  </v-card>
</template>

<style scoped>
.order-history-card {
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.trading-summary {
  background-color: #fafafa;
  border-radius: 8px;
  margin: 0 16px 16px;
}

.position-chip {
  font-size: 0.95rem;
  height: 32px;
}

.summary-cards {
  gap: 16px;
}

.summary-card {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  background-color: white;
  border: 1px solid #e0e0e0;
}

.card-header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.stat-row:last-child {
  margin-bottom: 0;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

.stat-value {
  font-weight: 600;
  font-size: 0.9rem;
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
  padding: 10px;
  margin-bottom: 8px;
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
  margin-bottom: 6px;
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
  font-size: 11px;
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
