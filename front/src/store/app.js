// store.js
import { defineStore } from "pinia";
import axios from '@/api/axios';
import { auth } from '@/firebaseConfig';
import { useAuthStore } from './auth';
import { useMarketStore } from './market';
import { useWebSocketStore } from './websocket';
import { useUIStore } from './ui';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut 
} from "firebase/auth";

export const useTraderStore = defineStore("trader", {
  state: () => ({
    // Core trader data
    traderUuid: null,
    trader: {
      shares: 0,
      cash: 0,
      initial_shares: 0,
    pnl: 0,
    vwap: 0,
      sum_dinv: 0,
    },
    
    // Trading state
    currentTime: null,
    isTradingStarted: false,
    remainingTime: null,
    
    // Market and game data
    tradingMarketData: {},
    gameParams: {},
    formState: null,
    
    // Orders
    placedOrders: [],
    executedOrders: [],
    
    // Trader attributes and progress
    traderAttributes: null,
    traderProgress: 0,
    
    // Market participants
    currentHumanTraders: 0,
    expectedHumanTraders: 0,
    allTradersReady: false,
    readyCount: 0,
    
    // Transaction tracking
    lastMatchedOrders: null,
    
    // Legacy/compatibility - deprecated but kept for backward compatibility
    step: 1000,
    messages: [],
  }),
  getters: {
    // Delegate to specialized stores while maintaining API compatibility
    bidData: () => useMarketStore().bidData,
    askData: () => useMarketStore().askData,
    chartData: () => useMarketStore().chartData,
    history: () => useMarketStore().history,
    midPoint: () => useMarketStore().midPoint,
    spread: () => useMarketStore().spread,
    extraParams: () => useMarketStore().extraParams,
    lastTransactionPrice: () => useMarketStore().lastTransactionPrice,
    recentTransactions: () => useMarketStore().recentTransactions,
    current_price: () => useMarketStore().currentPrice,
    
    // UI delegates
    showSnackbar: () => useUIStore().showSnackbar,
    snackbarText: () => useUIStore().snackbarText,
    dayOver: () => useUIStore().dayOver,
    intendedRoute: () => useUIStore().intendedRoute,
    
    // Auth delegates
    isAuthenticated: () => useAuthStore().isAuthenticated,
    user: () => useAuthStore().user,
    isAdmin: () => useAuthStore().isAdmin,
    
    // WebSocket delegates
    ws: () => useWebSocketStore().ws,
    
    // Trader-specific getters (maintain current API)
    shares: (state) => state.trader.shares,
    cash: (state) => state.trader.cash,
    initial_shares: (state) => state.trader.initial_shares,
    pnl: (state) => state.trader.pnl,
    vwap: (state) => state.trader.vwap,
    sum_dinv: (state) => state.trader.sum_dinv,
    
    goalMessage: (state) => {
      if (!state.traderAttributes || state.traderAttributes.goal === 0) return null;

      const goalAmount = state.traderAttributes.goal;
      const successVerb = goalAmount > 0 ? 'buying' : 'selling';
      const currentDelta = goalAmount - state.traderProgress;
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
    
    ws_path: (state) => {
      return `${import.meta.env.VITE_WS_URL}trader/${state.traderUuid}`;
    },
    
    activeOrders: (state) => state.placedOrders.filter(order => order.status === 'active'),
    pendingOrders: (state) => state.placedOrders.filter(order => order.status === 'pending'),
    
    hasExceededMaxShortShares: (state) => {
      if (state.gameParams.max_short_shares < 0) return false;
      return (
        state.trader.shares < 0 &&
        Math.abs(state.trader.shares) >= state.gameParams.max_short_shares
      );
    },
    
    hasExceededMaxShortCash: (state) => {
      if (state.gameParams.max_short_cash < 0) return false;
      return (
        state.trader.cash < 0 &&
        Math.abs(state.trader.cash) >= state.gameParams.max_short_cash
      );
    },
    
    hasReachedMaxActiveOrders(state) {
      return this.activeOrders.length >= state.gameParams.max_active_orders;
    },
    
    getSnackState(state) {
      if (
        this.hasExceededMaxShortCash ||
        this.hasExceededMaxShortShares ||
        this.hasReachedMaxActiveOrders
      ) {
        return true;
      }
      return false;
    },
  },
  actions: {
    // Initialize stores and setup message routing
    initializeStores() {
      const wsStore = useWebSocketStore();
      // Override WebSocket message handler to route to our handle_update
      wsStore.handleMessage = (data) => {
        if (data.type === "trader_id_confirmation") {
          this.confirmTraderId(data.data);
        } else {
          this.handle_update(data);
        }
      };
    },

    // Delegate to market store
    updateExtraParams(data) {
      useMarketStore().updateExtraParams(data);
    },

    async initializeTradingSystem(persistentSettings) {
      try {
        const response = await axios.post("trading/initiate");
        this.tradingMarketData = response.data.data;
        this.gameParams = persistentSettings;
        this.formState = this.gameParams;
        console.log("Game parameters:", this.gameParams); // Debug logging
      } catch (error) {
        throw error;
      }
    },

    async initializeTradingSystemWithPersistentSettings() {
      try {
        const persistentSettings = await this.fetchPersistentSettings();
        console.log("Persistent settings:", persistentSettings);
        await this.initializeTradingSystem(persistentSettings);
      } catch (error) {
        console.error('Error initializing trading system with persistent settings:', error);
        if (error.response) {
          console.error('Response data:', error.response.data);
          console.error('Response status:', error.response.status);
        }
        throw error;
      }
    },

    async getTraderAttributes(traderId) {
      try {
        const response = await axios.get(`trader_info/${traderId}`);
        
        if (response.data.status === "success") {
          this.traderAttributes = response.data.data;
          this.traderUuid = traderId;
          // Initialize traderProgress based on initial filled orders
          // Ensure filled_orders exists before calculating progress
          const filledOrders = this.traderAttributes.filled_orders || [];
          this.traderProgress = this.calculateProgress(filledOrders);
        } else {
          throw new Error("Failed to fetch trader attributes");
        }
      } catch (error) {
        console.error("Error fetching trader attributes:", error);
      }
    },

    startTraderAttributesPolling() {
      // Fetch immediately
      this.getTraderAttributes(this.traderUuid);
      // Then fetch every 5 seconds (adjust as needed)
      setInterval(() => {
        this.getTraderAttributes(this.traderUuid);
      }, 5000);
    },

    async initializeTrader(traderUuid) {
      this.traderUuid = traderUuid;
      
      try {
        console.log("Initializing trader:", traderUuid);
        await this.getTraderAttributes(traderUuid);
        
        // Get the market info to initialize counts properly
        try {
          const response = await axios.get(`trader/${traderUuid}/market`);
          if (response.data.status === "success") {
            const marketData = response.data.data;
            console.log("Market data received:", marketData);
            
            // Update market data and counts
            this.tradingMarketData = {
              trading_market_uuid: marketData.trading_market_uuid,
              ...marketData
            };
            
            // Set initial counts based on predefined_goals length
            this.$patch({
              currentHumanTraders: marketData.human_traders.length,
              expectedHumanTraders: marketData.game_params.predefined_goals.length
            });
          }
        } catch (error) {
          console.error("Error fetching market data:", error);
        }
        
        // Initialize WebSocket after setting initial values
        this.initializeWebSocket();
      } catch (error) {
        console.error("Error initializing trader:", error);
      }
    },
    
    handle_update(data) {
      // Handle trader count updates
      if (data.type === "trader_count_update") {
        console.log("Received trader count update:", data.data);
        this.$patch({
          currentHumanTraders: data.data.current_human_traders,
          expectedHumanTraders: data.data.expected_human_traders
        });
        return;
      }

      // Handle time updates
      if (data.type === "time_update") {
        this.$patch({
          currentTime: new Date(data.data.current_time),
          isTradingStarted: data.data.is_trading_started,
          remainingTime: data.data.remaining_time,
        });
        return;
      }

      // Handle market status updates
      if (data.type === "market_status_update") {
        this.allTradersReady = data.data.all_ready;
        this.readyCount = data.data.ready_count;
        return;
      }

      const {
        order_book,
        history,
        spread,
        midpoint,
        transaction_price,
        inventory,
        trader_orders,
        pnl,
        vwap,
        sum_dinv,
        initial_shares,
        matched_orders,
        type,
        goal,
        goal_progress
      } = data;

      // Update trader attributes
      if (goal !== undefined || goal_progress !== undefined) {
        this.traderAttributes = {
          ...this.traderAttributes,
          goal: goal !== undefined ? goal : this.traderAttributes?.goal,
          goal_progress: goal_progress !== undefined ? goal_progress : this.traderAttributes?.goal_progress
        };
      }

      // Handle transactions
      if (type === "transaction_update" && matched_orders) {
        this.handleFilledOrder(matched_orders, transaction_price);
      }

      // Update market data via market store
      if (transaction_price || midpoint || spread || history !== undefined) {
        useMarketStore().updateMarketData({ spread, midpoint, history, transaction_price });
      }

      // Update market extra params
      if (transaction_price && midpoint && spread) {
        this.updateExtraParams({ transaction_price, midpoint, spread });
      }

      // Update order book via market store
      if (order_book) {
        useMarketStore().updateOrderBook(order_book, this.gameParams);
      }

      // Update trader orders
      if (trader_orders) {
        this.placedOrders = trader_orders.map(order => ({
          ...order,
          order_type: order.order_type,
          status: 'active'
        }));
      }

      // Update trader data
      if (inventory) {
        const { shares, cash } = inventory;
        this.trader.shares = shares;
        this.trader.cash = cash;
      }

      if (pnl !== undefined) {
        this.trader.pnl = pnl;
      }
      
      if (initial_shares !== undefined) {
        this.trader.initial_shares = initial_shares;
      }

      if (sum_dinv !== undefined) {
        this.trader.sum_dinv = sum_dinv;
      }

      if (vwap !== undefined) {
        this.trader.vwap = vwap;
      }
    },

    handleFilledOrder(matched_orders, transaction_price) {
      // Update local state
      this.lastMatchedOrders = matched_orders;

      // Check if this trader is involved in the transaction
      const isInvolvedInTransaction = 
        matched_orders.bid_trader_id === this.traderUuid || 
        matched_orders.ask_trader_id === this.traderUuid;

      // Add transaction to market store for all traders (for display purposes)
      // But don't duplicate inventory updates - those are handled by the backend trader system
      useMarketStore().addTransaction({
        ...matched_orders,
        price: transaction_price,
        amount: matched_orders.transaction_amount,
        timestamp: new Date().toISOString(),
        isRelevantToTrader: isInvolvedInTransaction
      });

      if (isInvolvedInTransaction) {
        // Determine which order (bid or ask) belongs to this trader
        const isBid = matched_orders.bid_trader_id === this.traderUuid;
        const relevantOrderId = isBid ? matched_orders.bid_order_id : matched_orders.ask_order_id;

        // For passive orders, we only want to update the status, not add to executedOrders
        const isPassive = (isBid && matched_orders.initiator === 'ask') || 
                         (!isBid && matched_orders.initiator === 'bid');

        // Update the status of the relevant order
        this.updateOrderStatus(relevantOrderId, 'executed', isPassive);

        // NOTE: Inventory updates (shares, cash) and trader progress are now handled 
        // by the backend trader system via send_message_to_traders, not here.
        // This avoids double processing the same transaction.

        // Show notification for relevant trades
        useUIStore().showSnackbar(
          `Trade executed: ${matched_orders.transaction_amount} @ ${transaction_price}`,
          'success'
        );
      }

      // Notify components about the new transaction
      this.notifyTransactionOccurred(isInvolvedInTransaction);
    },

    updateOrderStatus(orderId, newStatus, isPassive) {
      const orderIndex = this.placedOrders.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex];
        order.status = newStatus;
        
        if (newStatus === 'executed' && !isPassive) {
          // Only add to executedOrders if it's not a passive order
          this.executedOrders.push({ ...order });
        }
        this.placedOrders.splice(orderIndex, 1);
      }
    },

    notifyTransactionOccurred(isRelevantToTrader) {
    },

    // Delegate WebSocket operations
    async initializeWebSocket() {
      this.initializeStores(); // Setup message routing first
      await useWebSocketStore().initializeWebSocket(this.traderUuid);
    },
    
    async sendMessage(type, data) {
      await useWebSocketStore().sendMessage(type, data);
    },

    // Delegate UI operations
    checkLimits() {
      useUIStore().showLimitMessage(
        this.gameParams,
        this.hasReachedMaxActiveOrders,
        this.hasExceededMaxShortCash,
        this.hasExceededMaxShortShares
      );
    },

    setIntendedRoute(route) {
      useUIStore().setIntendedRoute(route);
    },

    getIntendedRoute() {
      return useUIStore().getIntendedRoute();
    },

    addOrder(order) {
      // Normalize the order type
      const normalizedOrderType = this.normalizeOrderType(order.order_type);
    
      const newOrder = {
        ...order,
        id: `pending_${Date.now()}`, // Temporary ID until we get a response from the server
        status: 'pending',
        order_type: normalizedOrderType
      };
      this.placedOrders.push(newOrder);
      
      const message = {
        type: normalizedOrderType === 'BUY' ? 1 : -1,
        price: order.price,
        amount: order.amount
      };
    
      this.sendMessage("add_order", message);
    },
    
    // Helper method to normalize order type, as we havent finished refactoring all code and current use is mixed
    normalizeOrderType(orderType) {
      if (typeof orderType === 'string') {
        return orderType.toUpperCase() === 'BUY' ? 'BUY' : 'SELL';
      } else if (typeof orderType === 'number') {
        return orderType === 1 ? 'BUY' : 'SELL';
      }
      throw new Error('Invalid order type');
    },
    
    cancelOrder(orderId) {
      const orderIndex = this.placedOrders.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex];
        this.sendMessage("cancel_order", { id: orderId });
        this.placedOrders.splice(orderIndex, 1);
      }
    },
    
    // Delegate authentication operations
    async login(email, password) {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
      return userCredential.user.is_admin;
    },
    
    async register(email, password) {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      return userCredential.user.is_admin;
    },
    
    async logout() {
        await signOut(auth);
      useAuthStore().logout();
    },
    
    setAuthenticated(value) {
      // This is handled by auth store automatically
    },
    updateTimeInfo(data) {
      this.remainingTime = data.remaining_time;
      this.isTradingStarted = data.is_trading_started;
      this.currentHumanTraders = data.current_human_traders;
      this.expectedHumanTraders = data.expected_human_traders;
    },
    processWebSocketMessage(message) {
      if (message.type === 'time_update') {
        this.updateTimeInfo(message.data);
      }
    },

    calculateProgress(filledOrders) {
      if (!filledOrders || !Array.isArray(filledOrders)) {
        return 0; // Return 0 if filledOrders is undefined or not an array
      }
      return filledOrders.reduce((sum, order) => {
        const amount = order.amount || 1; // Default to 1 if amount is not specified
        return sum + (order.order_type === 'BID' ? amount : -amount);
      }, 0);
    },

    // Missing method that's used by WebSocket handler
    confirmTraderId(data) {
      console.log("Trader ID confirmed:", data);
    },

    clearStore() {
      // Reset all state properties to their initial values
      this.$reset();
      // Also clear other stores but only if they exist
      try {
        useMarketStore().$reset();
        useUIStore().$reset();
        useWebSocketStore().disconnect();
      } catch (e) {
        // Stores might not be initialized yet
      }
    },

    async fetchMarketMetrics() {
      if (!this.traderUuid || !this.tradingMarketData.trading_market_uuid) {
        console.error('Trader ID or Market ID is missing');
        return;
      }

      try {
        const response = await axios.get('/market_metrics', {
          params: {
            trader_id: this.traderUuid,
            market_id: this.tradingMarketData.trading_market_uuid
          },
          responseType: 'blob',
        });

        // Create a Blob from the CSV data
        const blob = new Blob([response.data], { type: 'text/csv' });
        
        // Create a link element and trigger the download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `market_${this.tradingMarketData.trading_market_uuid}_trader_${this.traderUuid}_metrics.csv`;
        
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

      } catch (error) {
        console.error('Error fetching market metrics:', error);
        if (error.response) {
          console.error('Response data:', error.response.data);
          console.error('Response status:', error.response.status);
        }
      }
    },

    async fetchPersistentSettings() {
      try {
        const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`);
        return response.data.data;
      } catch (error) {
        console.error('Error fetching persistent settings:', error);
        throw error;
      }
    },
    
    async updatePersistentSettings(settings) {
      try {
        await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, { settings });
      } catch (error) {
        console.error('Error updating persistent settings:', error);
        throw error;
      }
    },

    async initializeTradingSystemWithPersistentSettings() {
      try {
        const persistentSettings = await this.fetchPersistentSettings();
        await this.initializeTradingSystem(persistentSettings);
      } catch (error) {
        console.error('Error initializing trading system with persistent settings:', error);
        if (error.response) {
          console.error('Response data:', error.response.data);
          console.error('Response status:', error.response.status);
        }
        throw error;
      }
    },

    async startTradingMarket() {
      try {
        const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}trading/start`);
        if (response.data.status === "success") {
          // You might want to update some state here, e.g.:
          // this.isTradingStarted = true;
        }
      } catch (error) {
        console.error('Error starting trading market:', error);
        if (error.response) {
          console.error('Response data:', error.response.data);
          console.error('Response status:', error.response.status);
        }
        throw error;
      }
    },
  },
});

