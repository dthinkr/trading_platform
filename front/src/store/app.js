// store.js
import { defineStore } from "pinia";
import axios from '@/api/axios';
import { auth } from '@/firebaseConfig'
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut 
} from "firebase/auth";

function findMidpoint(bids, asks) {
  if (!bids.length || !asks.length) {
    return 0;
  }

  const largestBidX = Math.max(...bids.map(bid => bid.x));
  const lowestAskX = Math.min(...asks.map(ask => ask.x));
  const midpoint = (largestBidX + lowestAskX) / 2;

  return midpoint;
}

export const useTraderStore = defineStore("trader", {
  state: () => ({
    isAuthenticated: false,
    intendedRoute: null,
    dayOver: false,
    midPoint: 0,
    pnl: 0,
    vwap: 0,
    currentTime: null,
    isTradingStarted: false,
    remainingTime: null,
    tradingSessionData: {},
    formState: null, 
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
        explanation: 'Difference between the best bid and best ask',
        value: null
      },
      {
        var_name: 'midpoint',
        display_name: 'Midpoint',
        explanation: 'Midpoint between the best bid and best ask',
        value: null
      },

    ],
    step: 1000,
    traderUuid: null,
    gameParams: {},
    messages: [],
    status: null,
    data: [],
    bidData: [],
    askData: [],
    chartData: [
      {
        name: "Bids",
        color: "blue",
        data: [[1, 2]],
      },
      {
        name: "Asks",
        color: "red",
        data: [[1, 2]],
      },
    ],
    history: [],
    ws: null,
    spread: null,
    shares: 0,
    cash: 0,
    sum_dinv: 0,
    initial_shares: 0,
    current_price: null,
    placedOrders: [],
    executedOrders: [],
    showSnackbar: false,
    snackbarText: "",
    user: null,
    isAdmin: false,
    currentHumanTraders: 0,
    expectedHumanTraders: 0,
    traderAttributes: null,
    lastMatchedOrders: null,
    lastTransactionPrice: null,
    recentTransactions: [],
    traderProgress: 0,
    allTradersReady: false,
    readyCount: 0,
  }),
  getters: {
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
        state.shares < 0 &&
        Math.abs(state.shares) >= state.gameParams.max_short_shares
      );
    },
    hasExceededMaxShortCash: (state) => {
      if (state.gameParams.max_short_cash < 0) return false;
      return (
        state.cash < 0 &&
        Math.abs(state.cash) >= state.gameParams.max_short_cash
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
    updateExtraParams(data) {
      this.extraParams = this.extraParams.map(param => ({
        ...param,
        value: data[param.var_name] !== undefined ? data[param.var_name].toString() : param.value,
      }));
    },

    async initializeTradingSystem(persistentSettings) {
      try {
        const response = await axios.post("trading/initiate");
        this.tradingSessionData = response.data.data;
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
          this.traderProgress = this.calculateProgress(this.traderAttributes.filled_orders);
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
        await this.getTraderAttributes(traderUuid);
        this.initializeWebSocket();
      } catch (error) {
        // Handle error
      }
    },
    
    handle_update(data) {
      if (data.type === "time_update") {
        this.$patch({
          currentTime: new Date(data.data.current_time),
          isTradingStarted: data.data.is_trading_started,
          remainingTime: data.data.remaining_time,
          currentHumanTraders: data.data.current_human_traders,
          expectedHumanTraders: data.data.expected_human_traders
        });
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
        goal,           // Add these lines
        goal_progress   // Add these lines
      } = data;

      // Update trader attributes whenever we receive a message
      if (goal !== undefined || goal_progress !== undefined) {
        this.traderAttributes = {
          ...this.traderAttributes,
          goal: goal !== undefined ? goal : this.traderAttributes?.goal,
          goal_progress: goal_progress !== undefined ? goal_progress : this.traderAttributes?.goal_progress
        };
      }

      // Handle matched orders if present
      if (type === "transaction_update" && matched_orders) {
        this.handleFilledOrder(matched_orders, transaction_price);
      }

      if (transaction_price && midpoint && spread) {
        const market_level_data = {
          transaction_price,
          midpoint,
          spread
        };
        this.updateExtraParams(market_level_data);
      }

      if (trader_orders) {
        this.placedOrders = trader_orders.map(order => ({
          ...order,
          order_type: order.order_type,
          status: 'active'
        }));
      }

      if (inventory) {
        const { shares, cash } = inventory;
        this.shares = shares;
        this.cash = cash;
      }

      if (order_book) {
        const { bids, asks } = order_book;
        const depth_book_shown = this.gameParams.depth_book_shown || 3;
        this.bidData = bids.slice(0, depth_book_shown);
        this.askData = asks.slice(0, depth_book_shown);
        this.sum_dinv = sum_dinv;
        this.initial_shares = initial_shares;

        this.midPoint = midpoint || findMidpoint(bids, asks);
        this.chartData = [
          {
            name: "Bids",
            color: "blue",
            data: this.bidData,
          },
          {
            name: "Asks",
            color: "red",
            data: this.askData,
          },
        ];

        this.history = history;
        this.spread = spread;
        this.pnl = pnl;
        this.vwap = vwap;
      }

      if (data.type === "session_status_update") {
        this.allTradersReady = data.data.all_ready;
        this.readyCount = data.data.ready_count;
        // ... handle other status updates
      }
    },

    handleFilledOrder(matched_orders, transaction_price) {

      // Update your store state
      this.lastMatchedOrders = matched_orders;
      this.lastTransactionPrice = transaction_price;

      // Check if this trader is involved in the transaction
      const isInvolvedInTransaction = 
        matched_orders.bid_trader_id === this.traderUuid || 
        matched_orders.ask_trader_id === this.traderUuid;

      // Add this transaction to the list of recent transactions
      this.recentTransactions.push({
        ...matched_orders,
        price: transaction_price,
        timestamp: new Date().toISOString(),
        isRelevantToTrader: isInvolvedInTransaction
      });

      if (isInvolvedInTransaction) {
        
        // Determine which order (bid or ask) belongs to this trader
        const isBid = matched_orders.bid_trader_id === this.traderUuid;
        const relevantOrderId = isBid ? matched_orders.bid_order_id : matched_orders.ask_order_id;

        // Update the status of the relevant order
        this.updateOrderStatus(relevantOrderId, 'executed');

        // Update traderProgress
        const amount = matched_orders.amount || 1;
        this.traderProgress += isBid ? amount : -amount;
      }

      // Notify components about the new transaction
      this.notifyTransactionOccurred(isInvolvedInTransaction);
    },

    updateOrderStatus(orderId, newStatus) {
      const orderIndex = this.placedOrders.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex];
        order.status = newStatus;
        
        if (newStatus === 'executed') {
          this.executedOrders.push({ ...order });
          this.placedOrders.splice(orderIndex, 1);
        }
      }
    },

    notifyTransactionOccurred(isRelevantToTrader) {
    },

    async initializeWebSocket() {
      const wsUrl = `${import.meta.env.VITE_WS_URL}trader/${this.traderUuid}`;
      this.ws = new WebSocket(wsUrl);
    
      this.ws.onopen = async (event) => {
        const token = await auth.currentUser.getIdToken();
        this.ws.send(token);
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
        // Handle error
      };
    
      this.ws.onclose = (event) => {
        // Handle close
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

    checkLimits() {
      if (this.hasReachedMaxActiveOrders) {
        this.snackbarText = `You are allowed to have a maximum of ${this.gameParams.max_active_orders} active orders`;
        this.showSnackbar = true;
      } else if (this.hasExceededMaxShortCash) {
        this.snackbarText = `You are not allowed to short more than ${this.gameParams.max_short_cash} cash`;
        this.showSnackbar = true;
      } else if (this.hasExceededMaxShortShares) {
        this.snackbarText = `You are not allowed to short more than ${this.gameParams.max_short_shares} shares`;
        this.showSnackbar = true;
      }
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
    
    async login(email, password) {
      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        this.user = userCredential.user;
        this.isAuthenticated = true;
        this.isAdmin = userCredential.user.is_admin;
        return this.isAdmin;
      } catch (error) {
        throw error;
      }
    },
    
    async register(email, password) {
      try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        this.user = userCredential.user;
        this.isAuthenticated = true;
        this.isAdmin = userCredential.user.is_admin;
        return this.isAdmin;
      } catch (error) {
        throw error;
      }
    },
    async logout() {
      try {
        await signOut(auth);
        this.user = null;
        this.isAuthenticated = false;
        this.isAdmin = false;
      } catch (error) {
        throw error;
      }
    },
    setAuthenticated(value) {
      this.isAuthenticated = value;
    },
    setIntendedRoute(route) {
      this.intendedRoute = route;
    },
    getIntendedRoute() {
      const route = this.intendedRoute;
      this.intendedRoute = null;
      return route;
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
      return filledOrders.reduce((sum, order) => {
        const amount = order.amount || 1; // Default to 1 if amount is not specified
        return sum + (order.order_type === 'BID' ? amount : -amount);
      }, 0);
    },

    clearStore() {
      // Reset all state properties to their initial values
      this.$reset();
    },

    async fetchSessionMetrics() {
      if (!this.traderUuid || !this.tradingSessionData.trading_session_uuid) {
        console.error('Trader ID or Session ID is missing');
        return;
      }

      try {
        const response = await axios.get('/session_metrics', {
          params: {
            trader_id: this.traderUuid,
            session_id: this.tradingSessionData.trading_session_uuid
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
        a.download = `session_${this.tradingSessionData.trading_session_uuid}_trader_${this.traderUuid}_metrics.csv`;
        
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

      } catch (error) {
        console.error('Error fetching session metrics:', error);
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

    async startTradingSession() {
      try {
        const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}trading/start`);
        if (response.data.status === "success") {
          // You might want to update some state here, e.g.:
          // this.isTradingStarted = true;
        }
      } catch (error) {
        console.error('Error starting trading session:', error);
        if (error.response) {
          console.error('Response data:', error.response.data);
          console.error('Response status:', error.response.status);
        }
        throw error;
      }
    },
  },
});

