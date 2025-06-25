import { defineStore } from "pinia";

function findMidpoint(bids, asks) {
  if (!bids.length || !asks.length) {
    return 0;
  }

  const largestBidX = Math.max(...bids.map(bid => bid.x));
  const lowestAskX = Math.min(...asks.map(ask => ask.x));
  const midpoint = (largestBidX + lowestAskX) / 2;

  return midpoint;
}

export const useMarketStore = defineStore("market", {
  state: () => ({
    orderBook: {
      bids: [],
      asks: [],
      spread: null,
      midpoint: 0,
    },
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
    currentPrice: null,
    lastTransactionPrice: null,
    recentTransactions: [],
  }),

  getters: {
    bidData: (state) => state.orderBook.bids,
    askData: (state) => state.orderBook.asks,
    midPoint: (state) => state.orderBook.midpoint,
    spread: (state) => state.orderBook.spread,
  },

  actions: {
    updateOrderBook(orderBook, gameParams) {
      if (!orderBook) return;

      const { bids, asks } = orderBook;
      const depthBookShown = gameParams?.depth_book_shown || 3;
      
      this.orderBook.bids = bids.slice(0, depthBookShown);
      this.orderBook.asks = asks.slice(0, depthBookShown);
      this.orderBook.midpoint = findMidpoint(this.orderBook.bids, this.orderBook.asks);

      this.chartData = [
        {
          name: "Bids",
          color: "blue",
          data: this.orderBook.bids,
        },
        {
          name: "Asks",
          color: "red",
          data: this.orderBook.asks,
        },
      ];
    },

    updateMarketData({ spread, midpoint, history, transaction_price }) {
      if (spread !== undefined) {
        this.orderBook.spread = spread;
      }
      if (midpoint !== undefined) {
        this.orderBook.midpoint = midpoint;
      }
      if (history !== undefined) {
        this.history = history;
      }
      if (transaction_price !== undefined) {
        this.lastTransactionPrice = transaction_price;
        this.currentPrice = transaction_price;
      }
    },

    updateExtraParams(data) {
      this.extraParams = this.extraParams.map(param => ({
        ...param,
        value: data[param.var_name] !== undefined ? data[param.var_name].toString() : param.value,
      }));
    },

    addTransaction(transaction) {
      this.recentTransactions.push(transaction);
    },
  },
}); 