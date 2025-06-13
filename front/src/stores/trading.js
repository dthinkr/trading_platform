import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/api/axios'
import { useAuthStore } from './auth'

export const useTradingStore = defineStore('trading', () => {
  // State
  const ws = ref(null)
  const isConnected = ref(false)
  const isTradingStarted = ref(false)
  const dayOver = ref(false)
  const isStartingTrading = ref(false)
  
  // Market data
  const orderBook = ref({ bids: [], asks: [] })
  const recentTransactions = ref([])
  const priceHistory = ref([])
  const currentPrice = ref(null)
  const midPoint = ref(0)
  const spread = ref(null)
  
  // Trader data
  const traderAttributes = ref(null)
  const cash = ref(0)
  const shares = ref(0)
  const initialCash = ref(0)
  const initialShares = ref(0)
  const pnl = ref(0)
  const vwap = ref(0)
  const sumDinv = ref(0)
  
  // Orders
  const activeOrders = ref([])
  const orderHistory = ref([])
  const filledOrders = ref([])
  
  // Game parameters
  const gameParams = ref({})
  const remainingTime = ref(null)
  const currentHumanTraders = ref(0)
  const expectedHumanTraders = ref(0)
  
  // Messages and notifications
  const messages = ref([])
  const notifications = ref([])
  
  // Computed properties
  const hasGoal = computed(() => 
    traderAttributes.value && traderAttributes.value.goal !== 0
  )
  
  const goal = computed(() => 
    traderAttributes.value ? traderAttributes.value.goal : 0
  )
  
  const goalProgress = computed(() => 
    traderAttributes.value ? traderAttributes.value.goal_progress : 0
  )
  
  const isGoalAchieved = computed(() => {
    if (!hasGoal.value) return false
    return Math.abs(goalProgress.value) >= Math.abs(goal.value)
  })
  
  const goalMessage = computed(() => {
    if (!hasGoal.value) return null
    
    const goalAmount = goal.value
    const currentProgress = goalProgress.value
    const remaining = Math.abs(goalAmount - currentProgress)
    
    if (remaining === 0) {
      return {
        text: `Goal achieved! You ${goalAmount > 0 ? 'bought' : 'sold'} ${Math.abs(goalAmount)} shares`,
        type: 'success'
      }
    }
    
    const action = goalAmount > 0 ? 'buy' : 'sell'
    return {
      text: `You need to ${action} ${remaining} more shares to reach your goal`,
      type: 'warning'
    }
  })
  
  const wsPath = computed(() => {
    const authStore = useAuthStore()
    return `${import.meta.env.VITE_WS_URL}trader/${authStore.traderId}`
  })
  
  const chartData = computed(() => {
    const bids = orderBook.value.bids.map(bid => ({ x: bid.x, y: bid.y }))
    const asks = orderBook.value.asks.map(ask => ({ x: ask.x, y: ask.y }))
    
    return [
      { name: 'Bids', data: bids, color: '#2196f3' },
      { name: 'Asks', data: asks, color: '#f44336' }
    ]
  })
  
  // Actions
  async function initializeWebSocket() {
    if (ws.value) {
      ws.value.close()
    }
    
    try {
      const authStore = useAuthStore()
      console.log('Initializing WebSocket for trader:', authStore.traderId)
      
      ws.value = new WebSocket(wsPath.value)
      
      ws.value.onopen = async () => {
        console.log('WebSocket connected, sending authentication...')
        
        // Send authentication token as first message
        try {
          // Get the current Firebase token or use Prolific token
          let token = 'no-auth' // Default for Prolific users
          
          if (authStore.user && !authStore.prolificToken) {
            // Firebase user - get fresh token
            const firebaseToken = await authStore.user.getIdToken()
            token = firebaseToken
            console.log('Sending Firebase token for authentication')
          } else if (authStore.prolificToken) {
            // Prolific user
            token = authStore.prolificToken
            console.log('Sending Prolific token for authentication')
          } else {
            console.log('Using no-auth for authentication')
          }
          
          ws.value.send(token)
          isConnected.value = true
          console.log('WebSocket authenticated successfully')
        } catch (authError) {
          console.error('WebSocket authentication failed:', authError)
          ws.value.close()
        }
      }
      
      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWebSocketMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
      
      ws.value.onclose = () => {
        isConnected.value = false
        console.log('WebSocket disconnected')
        // Auto-reconnect after 3 seconds
        setTimeout(() => {
          if (!dayOver.value) {
            initializeWebSocket()
          }
        }, 3000)
      }
      
      ws.value.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
    }
  }
  
  function handleWebSocketMessage(data) {
    const { type, ...payload } = data
    
    switch (type) {
      case 'order_book_update':
        orderBook.value = payload.order_book
        updateMidpoint()
        break
        
      case 'order_status_update':
        updateOrderStatus(payload)
        break
        
      case 'transaction':
        handleTransaction(payload)
        break
        
      case 'trader_update':
        updateTraderData(payload)
        break
        
      case 'trading_started':
        isTradingStarted.value = true
        break
        
      case 'trading_ended':
        dayOver.value = true
        break
        
      case 'time_update':
        remainingTime.value = payload.remaining_time
        break
        
      case 'traders_count':
        currentHumanTraders.value = payload.current
        expectedHumanTraders.value = payload.expected
        break
        
      case 'trader_count_update':
        currentHumanTraders.value = payload.data?.current_human_traders || payload.current_human_traders || 0
        expectedHumanTraders.value = payload.data?.expected_human_traders || payload.expected_human_traders || 0
        console.log(`Trader count updated: ${currentHumanTraders.value}/${expectedHumanTraders.value}`)
        
        // Check if we have enough traders and trading should start
        if (currentHumanTraders.value >= expectedHumanTraders.value && expectedHumanTraders.value > 0 && !isTradingStarted.value && !isStartingTrading.value) {
          console.log('Required number of traders reached, starting trading...')
          startTrading().catch(error => {
            console.error('Failed to start trading automatically:', error)
          })
        }
        break
        
      case 'market_message':
        messages.value.push({
          id: Date.now(),
          timestamp: new Date(),
          ...payload
        })
        break
        
      default:
        console.log('Unhandled message type:', type, payload)
    }
  }
  
  function updateMidpoint() {
    const bids = orderBook.value.bids
    const asks = orderBook.value.asks
    
    if (bids.length > 0 && asks.length > 0) {
      const bestBid = Math.max(...bids.map(bid => bid.x))
      const bestAsk = Math.min(...asks.map(ask => ask.x))
      midPoint.value = (bestBid + bestAsk) / 2
      spread.value = bestAsk - bestBid
    }
  }
  
  function updateOrderStatus(payload) {
    const order = activeOrders.value.find(o => o.id === payload.order_id)
    if (order) {
      order.status = payload.status
      
      if (payload.status === 'filled') {
        // Move to filled orders
        filledOrders.value.push({ ...order, ...payload })
        activeOrders.value = activeOrders.value.filter(o => o.id !== payload.order_id)
      } else if (payload.status === 'cancelled') {
        // Move to order history
        orderHistory.value.push({ ...order, status: 'cancelled' })
        activeOrders.value = activeOrders.value.filter(o => o.id !== payload.order_id)
      }
    }
  }
  
  function handleTransaction(payload) {
    currentPrice.value = payload.price
    recentTransactions.value.unshift({
      id: Date.now(),
      price: payload.price,
      quantity: payload.quantity,
      timestamp: new Date()
    })
    
    // Add to price history for charts
    priceHistory.value.push({
      price: payload.price,
      volume: payload.quantity,
      timestamp: new Date().toISOString()
    })
    
    // Keep only recent data (last 1000 points)
    if (recentTransactions.value.length > 100) {
      recentTransactions.value = recentTransactions.value.slice(0, 100)
    }
    if (priceHistory.value.length > 1000) {
      priceHistory.value = priceHistory.value.slice(-1000)
    }
  }
  
  function updateTraderData(payload) {
    cash.value = payload.cash
    shares.value = payload.shares
    pnl.value = payload.pnl
    vwap.value = payload.vwap
    sumDinv.value = payload.sum_dinv
    
    if (payload.goal_progress !== undefined) {
      if (traderAttributes.value) {
        traderAttributes.value.goal_progress = payload.goal_progress
      }
    }
  }
  
  async function placeOrder(orderType, price, quantity = 1) {
    try {
      const order = {
        id: `order_${Date.now()}`,
        type: orderType,
        price: price,
        quantity: quantity,
        status: 'pending',
        timestamp: new Date()
      }
      
      activeOrders.value.push(order)
      
      await sendWebSocketMessage('place_order', {
        type: orderType,
        price: price,
        amount: quantity
      })
      
      return order
    } catch (error) {
      console.error('Failed to place order:', error)
      throw error
    }
  }
  
  async function cancelOrder(orderId) {
    try {
      await sendWebSocketMessage('cancel_order', { id: orderId })
    } catch (error) {
      console.error('Failed to cancel order:', error)
      throw error
    }
  }
  
  async function sendWebSocketMessage(type, data) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, data }))
    } else {
      throw new Error('WebSocket not connected')
    }
  }
  
  async function fetchTraderAttributes(traderId) {
    try {
      const response = await axios.get(`trader_info/${traderId}`)
      if (response.data.status === 'success') {
        traderAttributes.value = response.data.data
        initialCash.value = response.data.data.initial_cash
        initialShares.value = response.data.data.initial_shares
        cash.value = response.data.data.initial_cash
        shares.value = response.data.data.initial_shares
      }
    } catch (error) {
      console.error('Failed to fetch trader attributes:', error)
      throw error
    }
  }
  
  async function fetchGameParams() {
    try {
      const response = await axios.get('admin/get_persistent_settings')
      if (response.data.status === 'success') {
        gameParams.value = response.data.data
      }
    } catch (error) {
      console.error('Failed to fetch game parameters:', error)
      throw error
    }
  }
  
  async function startTrading() {
    if (isStartingTrading.value) {
      console.log('Trading start already in progress...')
      return
    }
    
    try {
      isStartingTrading.value = true
      console.log('Calling /trading/start endpoint...')
      
      const response = await axios.post('/trading/start')
      console.log('Trading start response:', response.data)
      
      if (response.data.all_ready) {
        console.log('Trading started successfully!')
      } else {
        console.log(`Waiting for more traders: ${response.data.ready_count}/${response.data.total_needed}`)
      }
      
      return response.data
    } catch (error) {
      console.error('Failed to start trading:', error)
      throw error
    } finally {
      isStartingTrading.value = false
    }
  }
  
  function clearStore() {
    // Reset all state
    ws.value?.close()
    ws.value = null
    isConnected.value = false
    isTradingStarted.value = false
    dayOver.value = false
    orderBook.value = { bids: [], asks: [] }
    recentTransactions.value = []
    priceHistory.value = []
    currentPrice.value = null
    midPoint.value = 0
    spread.value = null
    traderAttributes.value = null
    cash.value = 0
    shares.value = 0
    initialCash.value = 0
    initialShares.value = 0
    pnl.value = 0
    vwap.value = 0
    sumDinv.value = 0
    activeOrders.value = []
    orderHistory.value = []
    filledOrders.value = []
    gameParams.value = {}
    remainingTime.value = null
    currentHumanTraders.value = 0
    expectedHumanTraders.value = 0
    messages.value = []
    notifications.value = []
  }
  
  return {
    // State
    ws,
    isConnected,
    isTradingStarted,
    dayOver,
    isStartingTrading,
    orderBook,
    recentTransactions,
    priceHistory,
    currentPrice,
    midPoint,
    spread,
    traderAttributes,
    cash,
    shares,
    initialCash,
    initialShares,
    pnl,
    vwap,
    sumDinv,
    activeOrders,
    orderHistory,
    filledOrders,
    gameParams,
    remainingTime,
    currentHumanTraders,
    expectedHumanTraders,
    messages,
    notifications,
    
    // Computed
    hasGoal,
    goal,
    goalProgress,
    isGoalAchieved,
    goalMessage,
    wsPath,
    chartData,
    
    // Actions
    initializeWebSocket,
    placeOrder,
    cancelOrder,
    sendWebSocketMessage,
    fetchTraderAttributes,
    fetchGameParams,
    startTrading,
    clearStore
  }
}) 