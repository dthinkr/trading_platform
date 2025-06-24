// store.js
import { defineStore } from "pinia";
import axios from '@/api/axios';
import { auth } from '@/firebaseConfig';
import { useAuthStore } from './auth';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut 
} from "firebase/auth";

// Utility functions
function findMidpoint(bids, asks) {
  if (!bids.length || !asks.length) {
    return 0;
  }
  const largestBidX = Math.max(...bids.map(bid => bid.x));
  const lowestAskX = Math.min(...asks.map(ask => ask.x));
  return (largestBidX + lowestAskX) / 2;
}

export const useTraderStore = defineStore("trader", {
  state: () => ({
    // Authentication & User State
    auth: {
      isAuthenticated: false,
      intendedRoute: null,
      user: null,
      isAdmin: false,
    },

    // Trader Core Data
    trader: {
      uuid: null,
      attributes: null,
      shares: 0,
      cash: 0,
      initial_shares: 0,
      initial_cash: 0,
      sum_dinv: 0,
      pnl: 0,
      vwap: 0,
      progress: 0,
    },

    // Market Data
    market: {
      data: {},
      params: {},
      midPoint: 0,
      spread: null,
      currentPrice: null,
      isTradingStarted: false,
      remainingTime: null,
      currentTime: null,
      currentHumanTraders: 0,
      expectedHumanTraders: 0,
      allTradersReady: false,
      readyCount: 0,
    },

    // Order Book & Chart Data
    orderBook: {
      bidData: [],
      askData: [],
      chartData: [
        { name: "Bids", color: "blue", data: [[1, 2]] },
        { name: "Asks", color: "red", data: [[1, 2]] }
      ],
      history: [],
    },

    // Trading Orders
    orders: {
      placed: [],
      executed: [],
      active: [],
      recent: [],
    },

    // Transaction Data
    transactions: {
      recent: [],
      lastMatched: null,
      lastPrice: null,
    },

    // Market Parameters & Extra Data
    extraParams: [
      {
        var_name: 'transaction_price',
        display_name: 'Transaction price',
        explanation: 'Price of the last transaction',
        value: null
      },
      {
        var_name: 'spread',
        display_name: 'Spread',
        explanation: 'Difference between the best bid and best ask prices',
        value: null
      },
      {
        var_name: 'midpoint',
        display_name: 'Midprice',
        explanation: 'Midprice between the best bid and best ask prices',
        value: null
      },
    ],

    // UI State
    ui: {
      showSnackbar: false,
      snackbarText: "",
      dayOver: false,
      step: 1000,
      status: null,
      data: [],
      messages: [],
      formState: null,
    },

    // WebSocket
    ws: null,
  }),

  getters: {
    // Authentication getters
    isAuthenticated: (state) => state.auth.isAuthenticated,
    user: (state) => state.auth.user,
    isAdmin: (state) => state.auth.isAdmin,

    // Trader getters
    traderUuid: (state) => state.trader.uuid,
    traderAttributes: (state) => state.trader.attributes,
    shares: (state) => state.trader.shares,
    cash: (state) => state.trader.cash,
    initial_shares: (state) => state.trader.initial_shares,
    pnl: (state) => state.trader.pnl,
    vwap: (state) => state.trader.vwap,
    sum_dinv: (state) => state.trader.sum_dinv,
    traderProgress: (state) => state.trader.progress,

    // Goal-related computed properties
    goal: (state) => state.trader.attributes?.goal || 0,
    goalProgress: (state) => state.trader.attributes?.goal_progress || 0,
    hasGoal: (state) => (state.trader.attributes?.goal || 0) !== 0,
    
    isGoalAchieved(state) {
      const goal = state.trader.attributes?.goal || 0;
      const progress = state.trader.attributes?.goal_progress || 0;
      if (goal === 0) return false;
      return Math.abs(progress) >= Math.abs(goal);
    },

    goalType(state) {
      const goal = state.trader.attributes?.goal || 0;
      if (goal === 0) return 'free';
      return goal > 0 ? 'buy' : 'sell';
    },

    goalMessage(state) {
      const goal = state.trader.attributes?.goal || 0;
      if (goal === 0) return null;

      const goalAmount = goal;
      const successVerb = goalAmount > 0 ? 'buying' : 'selling';
      const currentDelta = goalAmount - (state.trader.attributes?.goal_progress || 0);
      const remaining = Math.abs(currentDelta);
      const shareWord = remaining === 1 ? 'share' : 'shares';

      const action = currentDelta > 0 ? 'buy' : 'sell';
      if (remaining === 0) {
        return { 
          text: `You have reached your goal of ${successVerb} ${Math.abs(goalAmount)} shares`, 
          type: 'success' 
        };
      }

      return { 
        text: `You need to ${action} ${remaining} ${shareWord} to reach your goal`, 
        type: 'warning' 
      };
    },

    goalProgressPercentage(state) {
      const goal = state.trader.attributes?.goal || 0;
      const progress = state.trader.attributes?.goal_progress || 0;
      if (goal === 0) return 0;
      const targetGoal = Math.abs(goal);
      const currentProgress = Math.abs(progress);
      return Math.min((currentProgress / targetGoal) * 100, 100);
    },

    // Market getters
    gameParams: (state) => state.market.params,
    tradingMarketData: (state) => state.market.data,
    midPoint: (state) => state.market.midPoint,
    spread: (state) => state.market.spread,
    isTradingStarted: (state) => state.market.isTradingStarted,
    remainingTime: (state) => state.market.remainingTime,
    currentTime: (state) => state.market.currentTime,
    currentHumanTraders: (state) => state.market.currentHumanTraders,
    expectedHumanTraders: (state) => state.market.expectedHumanTraders,
    allTradersReady: (state) => state.market.allTradersReady,
    readyCount: (state) => state.market.readyCount,

    // Order book getters
    bidData: (state) => state.orderBook.bidData,
    askData: (state) => state.orderBook.askData,
    chartData: (state) => state.orderBook.chartData,
    history: (state) => state.orderBook.history,

    // Order getters
    placedOrders: (state) => state.orders.placed,
    executedOrders: (state) => state.orders.executed,
    activeOrders: (state) => state.orders.placed.filter(order => order.status === 'active'),
    pendingOrders: (state) => state.orders.placed.filter(order => order.status === 'pending'),

    // Transaction getters
    recentTransactions: (state) => state.transactions.recent,
    lastMatchedOrders: (state) => state.transactions.lastMatched,
    lastTransactionPrice: (state) => state.transactions.lastPrice,

    // Market calculations
    bestBid(state) {
      const bids = state.orderBook.bidData;
      return bids.length > 0 ? Math.max(...bids.map(bid => bid.x)) : null;
    },

    bestAsk(state) {
      const asks = state.orderBook.askData;
      return asks.length > 0 ? Math.min(...asks.map(ask => ask.x)) : null;
    },

    // Trading limits and validation
    hasExceededMaxShortShares: (state) => {
      const maxShort = state.market.params.max_short_shares;
      if (maxShort < 0) return false;
      return state.trader.shares < 0 && Math.abs(state.trader.shares) >= maxShort;
    },

    hasExceededMaxShortCash: (state) => {
      const maxShort = state.market.params.max_short_cash;
      if (maxShort < 0) return false;
      return state.trader.cash < 0 && Math.abs(state.trader.cash) >= maxShort;
    },

    hasReachedMaxActiveOrders(state) {
      const activeCount = state.orders.placed.filter(order => order.status === 'active').length;
      return activeCount >= (state.market.params.max_active_orders || Infinity);
    },

    getSnackState() {
      return this.hasExceededMaxShortCash || 
             this.hasExceededMaxShortShares || 
             this.hasReachedMaxActiveOrders;
    },

    // Formatted values
    formatDelta: (state) => {
      if (state.trader.sum_dinv == undefined) return "";
      const halfChange = Math.round(state.trader.sum_dinv);
      return halfChange >= 0 ? "+" + halfChange : halfChange.toString();
    },

    // UI helper getters
    goalTypeText(state) {
      const goal = state.trader.attributes?.goal || 0;
      if (goal === 0) return 'FREE';
      return goal > 0 ? 'BUY' : 'SELL';
    },

    roleDisplay(state) {
      const goal = state.trader.attributes?.goal || 0;
      if (goal === 0) {
        return {
          text: 'SPECULATOR',
          icon: 'mdi-account-search',
          color: 'teal'
        };
      }
      if (goal > 0) {
        return {
          text: 'INFORMED (BUY)',
          icon: 'mdi-trending-up',
          color: 'indigo'
        };
      }
      return {
        text: 'INFORMED (SELL)',
        icon: 'mdi-trending-down',
        color: 'deep-purple'
      };
    },

    progressBarColor(state) {
      const percentage = this.goalProgressPercentage;
      if (percentage === 100) return 'light-green accent-3';
      if (percentage > 75) return 'light-green lighten-1';
      if (percentage > 50) return 'amber lighten-1';
      if (percentage > 25) return 'orange lighten-1';
      return 'deep-orange lighten-1';
    },

    // WebSocket path
    ws_path: (state) => `${import.meta.env.VITE_WS_URL}trader/${state.trader.uuid}`,

    // UI getters
    showSnackbar: (state) => state.ui.showSnackbar,
    snackbarText: (state) => state.ui.snackbarText,
    dayOver: (state) => state.ui.dayOver,
  },

  actions: {
    // Authentication actions
    setAuthenticated(value) {
      this.auth.isAuthenticated = value;
    },

    setUser(user) {
      this.auth.user = user;
    },

    setAdmin(isAdmin) {
      this.auth.isAdmin = isAdmin;
    },

    setIntendedRoute(route) {
      this.auth.intendedRoute = route;
    },

    getIntendedRoute() {
      return this.auth.intendedRoute;
    },

    // Trader data actions
    updateTraderData(data) {
      // Update trader-specific data
      if (data.inventory) {
        this.trader.shares = data.inventory.shares;
        this.trader.cash = data.inventory.cash;
      }
      if (data.pnl !== undefined) this.trader.pnl = data.pnl;
      if (data.vwap !== undefined) this.trader.vwap = data.vwap;
      if (data.sum_dinv !== undefined) this.trader.sum_dinv = data.sum_dinv;
      if (data.initial_shares !== undefined) this.trader.initial_shares = data.initial_shares;
      if (data.goal !== undefined || data.goal_progress !== undefined) {
        this.trader.attributes = {
          ...this.trader.attributes,
          goal: data.goal !== undefined ? data.goal : this.trader.attributes?.goal,
          goal_progress: data.goal_progress !== undefined ? data.goal_progress : this.trader.attributes?.goal_progress
        };
      }
    },

    // Market data actions
    updateMarketData(data) {
      if (data.order_book) {
        const { bids, asks } = data.order_book;
        const depth_book_shown = this.market.params.depth_book_shown || 3;
        this.orderBook.bidData = bids.slice(0, depth_book_shown);
        this.orderBook.askData = asks.slice(0, depth_book_shown);

        this.market.midPoint = data.midpoint || findMidpoint(bids, asks);
        this.orderBook.chartData = [
          { name: "Bids", color: "blue", data: this.orderBook.bidData },
          { name: "Asks", color: "red", data: this.orderBook.askData }
        ];

        if (data.history !== undefined) this.orderBook.history = data.history;
        if (data.spread !== undefined) this.market.spread = data.spread;
      }

      if (data.transaction_price && data.midpoint && data.spread) {
        this.updateExtraParams({
          transaction_price: data.transaction_price,
          midpoint: data.midpoint,
          spread: data.spread
        });
      }
    },

    updateExtraParams(data) {
      this.extraParams = this.extraParams.map(param => ({
        ...param,
        value: data[param.var_name] !== undefined ? data[param.var_name].toString() : param.value,
      }));
    },

    // Order management actions
    updateOrders(data) {
      if (data.trader_orders) {
        this.orders.placed = data.trader_orders.map(order => ({
          ...order,
          order_type: order.order_type,
          status: 'active'
        }));
      }
    },

    addOrder(order) {
      const normalizedOrderType = this.normalizeOrderType(order.order_type);
      const newOrder = {
        ...order,
        id: `pending_${Date.now()}`,
        status: 'pending',
        order_type: normalizedOrderType
      };
      this.orders.placed.push(newOrder);
      
      const message = {
        type: normalizedOrderType === 'BUY' ? 1 : -1,
        price: order.price,
        amount: order.amount
      };
      this.sendMessage("add_order", message);
    },

    cancelOrder(orderId) {
      const orderIndex = this.orders.placed.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        this.sendMessage("cancel_order", { id: orderId });
        this.orders.placed.splice(orderIndex, 1);
      }
    },

    updateOrderStatus(orderId, newStatus, isPassive) {
      const orderIndex = this.orders.placed.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        const order = this.orders.placed[orderIndex];
        order.status = newStatus;
        
        if (newStatus === 'executed' && !isPassive) {
          this.orders.executed.push({ ...order });
        }
        this.orders.placed.splice(orderIndex, 1);
      }
    },

    normalizeOrderType(orderType) {
      const orderTypeMap = {
        'BUY': 'BUY', 'SELL': 'SELL',
        'BID': 'BUY', 'ASK': 'SELL',
        1: 'BUY', '-1': 'SELL', [-1]: 'SELL'
      };
      return orderTypeMap[orderType] || orderType;
    },

    // Transaction handling
    handleFilledOrder(matched_orders, transaction_price) {
      this.transactions.lastMatched = matched_orders;
      this.transactions.lastPrice = transaction_price;

      const isInvolvedInTransaction = 
        matched_orders.bid_trader_id === this.trader.uuid || 
        matched_orders.ask_trader_id === this.trader.uuid;

      this.transactions.recent.push({
        ...matched_orders,
        price: transaction_price,
        timestamp: new Date().toISOString(),
        isRelevantToTrader: isInvolvedInTransaction
      });

      if (isInvolvedInTransaction) {
        const isBid = matched_orders.bid_trader_id === this.trader.uuid;
        const relevantOrderId = isBid ? matched_orders.bid_order_id : matched_orders.ask_order_id;
        const isPassive = (isBid && matched_orders.initiator === 'ask') || 
                         (!isBid && matched_orders.initiator === 'bid');

        this.updateOrderStatus(relevantOrderId, 'executed', isPassive);

        const amount = matched_orders.amount || 1;
        this.trader.progress += isBid ? amount : -amount;
      }

      this.notifyTransactionOccurred(isInvolvedInTransaction);
    },

    notifyTransactionOccurred(isRelevantToTrader) {
      // Hook for transaction notifications
    },

    // Main update handler
    handle_update(data) {
      if (data.type === "trader_count_update") {
        this.market.currentHumanTraders = data.data.current_human_traders;
        this.market.expectedHumanTraders = data.data.expected_human_traders;
        return;
      }

      if (data.type === "time_update") {
        this.market.currentTime = new Date(data.data.current_time);
        this.market.isTradingStarted = data.data.is_trading_started;
        this.market.remainingTime = data.data.remaining_time;
        return;
      }

      if (data.type === "transaction_update" && data.matched_orders) {
        this.handleFilledOrder(data.matched_orders, data.transaction_price);
      }

      if (data.type === "market_status_update") {
        this.market.allTradersReady = data.data.all_ready;
        this.market.readyCount = data.data.ready_count;
        return;
      }

      // Update all data types
      this.updateTraderData(data);
      this.updateMarketData(data);
      this.updateOrders(data);
    },

    // Trading system initialization
    async initializeTradingSystem(persistentSettings) {
      try {
        const response = await axios.post("trading/initiate");
        this.market.data = response.data.data;
        this.market.params = persistentSettings;
        this.ui.formState = this.market.params;
      } catch (error) {
        throw error;
      }
    },

    async initializeTradingSystemWithPersistentSettings() {
      try {
        const persistentSettings = await this.fetchPersistentSettings();
        await this.initializeTradingSystem(persistentSettings);
      } catch (error) {
        console.error('Error initializing trading system:', error);
        throw error;
      }
    },

    // Trader management
    async getTraderAttributes(traderId) {
      try {
        const response = await axios.get(`trader_info/${traderId}`);
        
        if (response.data.status === "success") {
          this.trader.attributes = response.data.data;
          this.trader.uuid = traderId;
          this.trader.progress = this.calculateProgress(this.trader.attributes.filled_orders || []);
        } else {
          throw new Error("Failed to fetch trader attributes");
        }
      } catch (error) {
        console.error("Error fetching trader attributes:", error);
      }
    },

    async initializeTrader(traderUuid) {
      this.trader.uuid = traderUuid;
      
      try {
        await this.getTraderAttributes(traderUuid);
        
        try {
          const response = await axios.get(`trader/${traderUuid}/market`);
          if (response.data.status === "success") {
            const marketData = response.data.data;
            
            this.market.data = {
              trading_market_uuid: marketData.trading_market_uuid,
              ...marketData
            };
            
            this.market.currentHumanTraders = marketData.human_traders.length;
            this.market.expectedHumanTraders = marketData.game_params.predefined_goals.length;
          }
        } catch (error) {
          console.error("Error fetching market data:", error);
        }
        
        this.initializeWebSocket();
      } catch (error) {
        console.error("Error initializing trader:", error);
      }
    },

    calculateProgress(filledOrders) {
      if (!filledOrders || !Array.isArray(filledOrders)) {
        return 0;
      }
      return filledOrders.reduce((sum, order) => {
        const amount = order.amount || 1;
        return sum + (order.order_type === 'BID' ? amount : -amount);
      }, 0);
    },

    // WebSocket management
    async initializeWebSocket() {
      const wsUrl = `${import.meta.env.VITE_WS_URL}trader/${this.trader.uuid}`;
      this.ws = new WebSocket(wsUrl);
    
      this.ws.onopen = async (event) => {
        try {
          const authStore = useAuthStore();
          if (authStore.prolificToken) {
            this.ws.send(authStore.prolificToken);
          } else if (auth.currentUser) {
            const token = await auth.currentUser.getIdToken();
            this.ws.send(token);
          } else {
            this.ws.send("no-auth");
          }
        } catch (error) {
          console.error("Error sending authentication token:", error);
        }
      };
    
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "trader_id_confirmation") {
            this.confirmTraderId(data.data);
          } else {
            this.handle_update(data);
          }
        } catch (error) {
          console.error("Error processing WebSocket message:", error);
        }
      };
    
      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    
      this.ws.onclose = (event) => {
        console.log("WebSocket connection closed:", event.code, event.reason);
      };
    },
    
    async sendMessage(type, data) {
      if (this.ws.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({ type, data });
        this.ws.send(message);
      } else {
        console.warn(`WebSocket is not open. Current state: ${this.ws.readyState}`);
      }
    },

    // Validation helpers
    checkLimits() {
      if (this.hasReachedMaxActiveOrders) {
        this.ui.snackbarText = `You are allowed to have a maximum of ${this.market.params.max_active_orders} active orders`;
        this.ui.showSnackbar = true;
      } else if (this.hasExceededMaxShortCash) {
        this.ui.snackbarText = `You are not allowed to short more than ${this.market.params.max_short_cash} cash`;
        this.ui.showSnackbar = true;
      } else if (this.hasExceededMaxShortShares) {
        this.ui.snackbarText = `You are not allowed to short more than ${this.market.params.max_short_shares} shares`;
        this.ui.showSnackbar = true;
      }
    },

    // Authentication actions
    async login(email, password) {
      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        this.setAuthenticated(true);
        this.setUser(userCredential.user);
        return userCredential;
      } catch (error) {
        throw error;
      }
    },

    async register(email, password) {
      try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        this.setAuthenticated(true);
        this.setUser(userCredential.user);
        return userCredential;
      } catch (error) {
        throw error;
      }
    },

    async logout() {
      try {
        await signOut(auth);
        this.setAuthenticated(false);
        this.setUser(null);
      } catch (error) {
        throw error;
      }
    },

    // Data management
    updateTimeInfo(data) {
      this.market.remainingTime = data.remaining_time;
      this.market.isTradingStarted = data.is_trading_started;
      this.market.currentHumanTraders = data.current_human_traders;
      this.market.expectedHumanTraders = data.expected_human_traders;
    },

    clearStore() {
      this.$reset();
    },

    // Server interactions
    async fetchMarketMetrics() {
      // Implementation for fetching market metrics
    },

    async fetchPersistentSettings() {
      try {
        const response = await axios.get('admin/persistent_settings');
        return response.data.data;
      } catch (error) {
        console.error('Error fetching persistent settings:', error);
        return {};
      }
    },

    async updatePersistentSettings(settings) {
      try {
        const response = await axios.post('admin/update_persistent_settings', { settings });
        return response.data;
      } catch (error) {
        console.error('Error updating persistent settings:', error);
        throw error;
      }
    },

    async startTradingMarket() {
      try {
        const response = await axios.post('trading/start');
        return response.data;
      } catch (error) {
        console.error('Error starting trading market:', error);
        throw error;
      }
    },

    // Helper methods
    confirmTraderId(data) {
      // Handle trader ID confirmation
    },

    processWebSocketMessage(message) {
      // Process WebSocket messages
    },

    startTraderAttributesPolling() {
      this.getTraderAttributes(this.trader.uuid);
      setInterval(() => {
        this.getTraderAttributes(this.trader.uuid);
      }, 5000);
    }
  }
});

