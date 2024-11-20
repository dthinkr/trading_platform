<script setup>
import { computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const traderStore = useTraderStore();
const { executedOrders, recentTransactions, traderUuid } = storeToRefs(traderStore);

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
  };
});

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};
</script>

<template>
  <v-card height="100%" elevation="3" class="order-history-card">
    <div class="trading-summary pa-2">
      <div class="vwap-display">
        <div class="label">VWAP</div>
        <span class="vwap-item buy">{{ tradingSummary.buyVWAP }}</span>
        <span class="vwap-divider">|</span>
        <span class="vwap-item sell">{{ tradingSummary.sellVWAP }}</span>
      </div>
      <!-- <div class="count-display">
        <div class="label">Count</div>
        <span class="count-item buy">{{ tradingSummary.buyCount }}</span>
        <span class="count-divider">|</span>
        <span class="count-item sell">{{ tradingSummary.sellCount }}</span>
      </div> -->
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
  padding: 6px;
}

.vwap-display, .count-display {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 0.9rem;
  white-space: nowrap;
  position: relative;
}

.label {
  position: absolute;
  left: 0;
  font-size: 0.7rem;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
}

/* .count-display {
  margin-top: 4px;
  font-size: 0.8rem;
} */

.vwap-item, .count-item {
  font-weight: 500;
}

/* .count-divider {
  color: #999;
} */

.vwap-item.buy, .count-item.buy {
  color: #1976D2;
}

.vwap-item.sell, .count-item.sell {
  color: #D32F2F;
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
  padding: 2px 10px;
  margin-bottom: 4px;
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
  margin-bottom: 2px;
}

.price {
  font-size: 13px;
  font-weight: 600;
}

.amount {
  font-size: 11px;
  font-weight: 500;
  color: #666;
}

.time {
  font-size: 10px;
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
