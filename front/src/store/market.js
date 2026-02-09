import { defineStore } from 'pinia'

function findMidpoint(bids, asks) {
  if (!bids.length || !asks.length) {
    return 0
  }

  const largestBidX = Math.max(...bids.map((bid) => bid.x))
  const lowestAskX = Math.min(...asks.map((ask) => ask.x))
  const midpoint = (largestBidX + lowestAskX) / 2

  return midpoint
}

export const useMarketStore = defineStore('market', {
  state: () => ({
    orderBook: {
      bids: [],
      asks: [],
      spread: null,
      midpoint: 0,
    },
    anchorMid: null,
    anchorInitialized: false,
    chartData: [
      {
        name: 'Bids',
        color: 'blue',
        data: [[1, 2]],
      },
      {
        name: 'Asks',
        color: 'red',
        data: [[1, 2]],
      },
    ],
    history: [],
    extraParams: [
      {
        var_name: 'transaction_price',
        display_name: 'Transaction price',
        explanation: 'Price of the last transaction',
        value: null,
      },
      {
        var_name: 'spread',
        display_name: 'Spread',
        explanation: 'Difference between the best bid and best ask prices',
        value: null,
      },
      {
        var_name: 'midpoint',
        display_name: 'Midprice',
        explanation: 'Midprice between the best bid and best ask prices',
        value: null,
      },
      {
        var_name: 'noise_trader_status',
        display_name: 'Noise Trader Status',
        explanation: 'Current status of the noise trader (active or sleeping)',
        value: null,
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
      if (!orderBook) return

      const { bids, asks } = orderBook
      const depthBookShown = gameParams?.depth_book_shown || 8
      const adjEdge = gameParams?.adj_edge || 2
      const step = gameParams?.step || 1

      // Compute real midpoint from full (unfiltered) data
      const realMid = findMidpoint(bids, asks)

      // Initialize or update anchor mid-price
      if (!this.anchorInitialized && realMid > 0) {
        this.anchorMid = Math.round(realMid)
        this.anchorInitialized = true
      } else if (!this.anchorInitialized && gameParams?.default_price) {
        this.anchorMid = gameParams.default_price
      } else if (this.anchorInitialized && realMid > 0) {
        // Only re-center if mid drifts by adj_edge or more
        if (Math.abs(realMid - this.anchorMid) >= adjEdge) {
          this.anchorMid = Math.round(realMid)
        }
      }

      // Filter bids/asks to the anchor price range
      const minPrice = this.anchorMid - depthBookShown * step
      const maxPrice = this.anchorMid + depthBookShown * step

      this.orderBook.bids = bids.filter(b => b.x >= minPrice && b.x <= maxPrice)
      this.orderBook.asks = asks.filter(a => a.x >= minPrice && a.x <= maxPrice)
      this.orderBook.midpoint = realMid

      this.chartData = [
        {
          name: 'Bids',
          color: 'blue',
          data: this.orderBook.bids,
        },
        {
          name: 'Asks',
          color: 'red',
          data: this.orderBook.asks,
        },
      ]
    },

    updateMarketData({ spread, midpoint, history, transaction_price }) {
      if (spread !== undefined) {
        this.orderBook.spread = spread
      }
      if (midpoint !== undefined) {
        this.orderBook.midpoint = midpoint
      }
      if (history !== undefined) {
        this.history = history
      }
      if (transaction_price !== undefined) {
        this.lastTransactionPrice = transaction_price
        this.currentPrice = transaction_price
      }
    },

    updateExtraParams(data) {
      this.extraParams = this.extraParams.map((param) => ({
        ...param,
        value: data[param.var_name] !== undefined ? data[param.var_name].toString() : param.value,
      }))
    },

    addTransaction(transaction) {
      // Check for duplicates using bid_order_id and ask_order_id
      const isDuplicate = this.recentTransactions.some(
        (t) =>
          t.bid_order_id === transaction.bid_order_id &&
          t.ask_order_id === transaction.ask_order_id
      )
      
      if (!isDuplicate) {
        this.recentTransactions.push(transaction)
      }
    },
  },
})
