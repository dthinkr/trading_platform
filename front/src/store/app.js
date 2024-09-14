// store.js
import { defineStore } from "pinia";
import axios from '@/api/axios';
import { useWebSocket } from "@vueuse/core";
import { auth } from '@/firebaseConfig'
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut 
} from "firebase/auth";

function findMidpoint(bids, asks) {
  // Ensure the arrays are not empty
  if (!bids.length || !asks.length) {
    console.debug('One or both arrays are empty.');
    return 0; // Or any other default value you deem appropriate
  }

  // Find the largest x value in the bids array
  const largestBidX = Math.max(...bids.map(bid => bid.x));

  // Find the lowest x value in the asks array
  const lowestAskX = Math.min(...asks.map(ask => ask.x));

  // Calculate the midpoint
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
  }),
  getters: {
    goalMessage: (state) => {
      if (state.gameParams.goal === 0) return null;


      const goalAmount = state.gameParams.goal;
      const successVerb = state.gameParams.goal > 0 ? 'buying' : 'selling';
      const currentDelta = goalAmount - state.sum_dinv;
      const remaining = Math.abs(currentDelta);
      const shareWord = remaining === 1 ? 'share' : 'shares';

      const action = currentDelta > 0 ? 'buy' : 'sell';
      console.debug('goalAmount', goalAmount, 'successVerb', successVerb, 'currentDelta', currentDelta, 'remaining', remaining, 'shareWord', shareWord, 'action', action)
      if (remaining == 0) return { text: `You have reached your goal of ${successVerb} ${Math.abs(goalAmount)} shares`, type: 'success' };


      return { text: `You need to ${action} ${remaining}  ${shareWord} to reach your goal`, type: 'warning' };
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

  async initializeTradingSystem(formState) {
    try {
      const response = await axios.post("trading/initiate", formState);
      console.debug(response.data.data);
      this.tradingSessionData = response.data.data;

      // Store the formState in gameParams for future reference
      this.gameParams = formState;
      // Store the formState separately as well
      this.formState = formState;
      // Connect to WebSocket or perform other actions
    } catch (error) {
      console.error("Error initializing trading system:", error);
      throw error;
    }
    },

    async getTraderAttributes(traderId) {
      console.log("Getting trader attributes for:", traderId);
      try {
        const response = await axios.get(`trader_info/${traderId}`);
        console.log("Trader info response:", response);
        
        if (response.data.status === "success") {
          this.traderAttributes = response.data.data;
          this.traderUuid = traderId;
          console.log("Trader attributes set:", this.traderAttributes);
        } else {
          console.error("Failed to fetch trader attributes:", response.data);
          throw new Error("Failed to fetch trader attributes");
        }
      } catch (error) {
        console.error('Failed to fetch trader attributes:', error);
        throw error;
      }
    },

    async initializeTrader(traderUuid) {
      console.debug("Initializing trader");
      this.traderUuid = traderUuid;
      
      try {
        await this.getTraderAttributes(traderUuid);
        this.initializeWebSocket();
      } catch (error) {
        console.error("Error initializing trader:", error);
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
      } = data;
    
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
          order_type: order.order_type === 1 ? 'BID' : 'ASK',
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
    },

    async initializeWebSocket() {
      console.debug("Initializing WebSocket");
      const wsUrl = `${import.meta.env.VITE_WS_URL}trader/${this.traderUuid}`;
      this.ws = new WebSocket(wsUrl);
    
      this.ws.onopen = async (event) => {
        console.debug("WebSocket connected:", event);
        // Send authentication token
        const token = await auth.currentUser.getIdToken();
        this.ws.send(token);
      };
    
      this.ws.onmessage = (event) => {
        console.debug("WebSocket message received:", event.data);
        const data = JSON.parse(event.data);
        this.handle_update(data);
      };
    
      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    
      this.ws.onclose = (event) => {
        console.debug("WebSocket closed:", event);
      };
    },
    
    async sendMessage(type, data) {
      // Use the 'send' function from the state

      if (this.ws.status === "OPEN") {
        this.ws.send(JSON.stringify({ type, data }));
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
      this.placedOrders.push(order);
      this.sendMessage("add_order", { 
        type: order.order_type === 'BID' ? 1 : -1, // Convert to integer
        price: order.price,
        amount: order.amount 
      });
    },
    
    cancelOrder(orderId) {
      const orderIndex = this.placedOrders.findIndex(order => order.id === orderId);
      if (orderIndex !== -1) {
        const order = this.placedOrders[orderIndex];
        this.sendMessage("cancel_order", { id: orderId });
        this.placedOrders.splice(orderIndex, 1);
      }
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
    async login(email, password) {
      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        this.user = userCredential.user;
        this.isAuthenticated = true;
        this.isAdmin = userCredential.user.is_admin;
        return this.isAdmin;
      } catch (error) {
        console.error('Login failed:', error);
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
        console.error('Registration failed:', error);
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
        console.error('Logout failed:', error);
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
      this.intendedRoute = null; // Clear the intended route after retrieving it
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
  },
});
