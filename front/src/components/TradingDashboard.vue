<template>
  <div v-if="isInitialized" class="min-h-screen bg-neutral-50">
    <!-- Skip link for accessibility -->
    <a href="#trading-content" class="skip-link">Skip to trading content</a>
    
    <!-- Error Alert -->
    <div v-if="showErrorAlert" class="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
      <div class="rounded-md bg-red-50 p-4 shadow-lg" role="alert">
        <div class="flex">
          <ExclamationTriangleIcon class="h-5 w-5 text-red-400" aria-hidden="true" />
          <div class="ml-3">
            <p class="text-sm font-medium text-red-800">Connection error. Please refresh the page.</p>
            <button @click="refreshPage" class="mt-2 btn-secondary text-xs">
          Refresh Now
            </button>
          </div>
          <button @click="showErrorAlert = false" class="ml-auto">
            <XMarkIcon class="h-4 w-4 text-red-400" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>

    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-neutral-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo and Title -->
          <div class="flex items-center space-x-4">
            <div class="flex items-center space-x-2">
              <ChartBarIcon class="h-8 w-8 text-blue-600" aria-hidden="true" />
              <h1 class="text-xl font-bold text-neutral-900">Trading Dashboard</h1>
            </div>
          </div>

          <!-- Status Indicators -->
          <div class="flex items-center space-x-3">
            <!-- Role Badge -->
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" 
                  :class="roleColorClass">
              <component :is="roleIcon" class="w-3 h-3 mr-1" aria-hidden="true" />
                {{ roleDisplay.text }}
            </span>

            <!-- Stats -->
            <div class="hidden sm:flex items-center space-x-4 text-sm">
              <div class="flex items-center space-x-1">
                <CurrencyDollarIcon class="h-4 w-4 text-neutral-500" aria-hidden="true" />
                <span class="font-medium">PnL:</span>
                <span class="font-mono" :class="pnl >= 0 ? 'text-green-600' : 'text-red-600'">
                  {{ formatCurrency(pnl) }}
                </span>
              </div>
              <div class="flex items-center space-x-1">
                <CubeIcon class="h-4 w-4 text-neutral-500" aria-hidden="true" />
                <span class="font-medium">Shares:</span>
                <span class="font-mono">{{ initialShares }}{{ formatDelta }}</span>
              </div>
              <div class="flex items-center space-x-1">
                <BanknotesIcon class="h-4 w-4 text-neutral-500" aria-hidden="true" />
                <span class="font-medium">Cash:</span>
                <span class="font-mono">{{ formatCurrency(cash) }}</span>
              </div>
              <div class="flex items-center space-x-1">
                <UsersIcon class="h-4 w-4 text-neutral-500" aria-hidden="true" />
                <span class="font-medium">Traders:</span>
                <span class="font-mono">{{ currentHumanTraders }}/{{ expectedHumanTraders }}</span>
              </div>
            </div>

            <!-- Goal Progress -->
            <div v-if="hasGoal" class="flex items-center space-x-2">
              <div class="flex flex-col items-end">
                <span class="text-xs text-neutral-600">{{ goalTypeText }} Goal</span>
                <div class="flex items-center space-x-1">
                  <div class="w-16 bg-neutral-200 rounded-full h-2">
                    <div class="h-2 rounded-full transition-all duration-300" 
                         :class="progressBarColor" 
                         :style="{ width: goalProgressPercentage + '%' }"></div>
                  </div>
                  <span class="text-xs font-mono">{{ Math.abs(goalProgress) }}/{{ Math.abs(goal) }}</span>
                </div>
              </div>
            </div>

            <!-- Timer -->
            <div class="flex items-center space-x-1 px-3 py-1 bg-blue-50 rounded-lg">
              <ClockIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
              <span class="font-mono text-sm text-blue-800">
                <CountdownTimer v-if="remainingTime" :time="remainingTime" />
                <span v-else>Waiting to start</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main id="trading-content" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Trading Interface -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left Sidebar -->
        <div class="lg:col-span-3 space-y-6">
          <OrderHistory />
          <MarketMessages />
        </div>

        <!-- Main Trading Area -->
        <div class="lg:col-span-6 space-y-6">
          <OrderBookChart />
          <ActiveOrders />
        </div>

        <!-- Right Sidebar -->
        <div class="lg:col-span-3 space-y-6">
          <PriceHistory />
          <TradingPanel :is-goal-achieved="isGoalAchieved" :goal-type="goalType" />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>  
import { computed, watch, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ChartBarIcon,
  CurrencyDollarIcon,
  CubeIcon,
  BanknotesIcon,
  UsersIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  EyeIcon
} from '@heroicons/vue/24/outline'

// Components
import OrderHistory from './trading/OrderHistory.vue'
import MarketMessages from './trading/MarketMessages.vue'
import OrderBookChart from './trading/OrderBookChart.vue'
import ActiveOrders from './trading/ActiveOrders.vue'
import PriceHistory from './trading/PriceHistory.vue'
import TradingPanel from './trading/TradingPanel.vue'
import CountdownTimer from './ui/CountdownTimer.vue'

// Stores
import { useTradingStore } from '@/stores/trading'
import { useAuthStore } from '@/stores/auth'

// Router
const router = useRouter()

// Stores
const tradingStore = useTradingStore()
const authStore = useAuthStore()

// State
const showErrorAlert = ref(false)

// Props (from router params)
const props = defineProps({
  traderUuid: String,
  marketId: String
})

// Computed properties
const isInitialized = computed(() => 
  tradingStore.traderAttributes && authStore.traderId
)

const hasGoal = computed(() => tradingStore.hasGoal)
const goal = computed(() => tradingStore.goal)
const goalProgress = computed(() => tradingStore.goalProgress)
const isGoalAchieved = computed(() => tradingStore.isGoalAchieved)

const goalType = computed(() => {
  if (!hasGoal.value) return 'free'
  return goal.value > 0 ? 'buy' : 'sell'
})

const goalTypeText = computed(() => {
  if (!hasGoal.value) return 'FREE'
  return goal.value > 0 ? 'BUY' : 'SELL'
})

const goalProgressPercentage = computed(() => {
  if (!hasGoal.value) return 0
  const targetGoal = Math.abs(goal.value)
  const currentProgress = Math.abs(goalProgress.value)
  return Math.min((currentProgress / targetGoal) * 100, 100)
})

const progressBarColor = computed(() => {
  const percentage = goalProgressPercentage.value
  if (percentage === 100) return 'bg-green-500'
  if (percentage > 75) return 'bg-green-400'
  if (percentage > 50) return 'bg-yellow-400'
  if (percentage > 25) return 'bg-orange-400'
  return 'bg-red-400'
})

const roleDisplay = computed(() => {
  if (!hasGoal.value) {
    return {
      text: 'SPECULATOR',
      icon: EyeIcon,
      color: 'teal'
    }
  }
  
  if (goal.value > 0) {
    return {
      text: 'INFORMED (BUY)',
      icon: ArrowTrendingUpIcon,
      color: 'blue'
    }
  }
  
  return {
    text: 'INFORMED (SELL)',
    icon: ArrowTrendingDownIcon,
    color: 'red'
  }
})

const roleIcon = computed(() => roleDisplay.value.icon)

const roleColorClass = computed(() => {
  const color = roleDisplay.value.color
  const colorMap = {
    teal: 'bg-teal-100 text-teal-800',
    blue: 'bg-blue-100 text-blue-800',
    red: 'bg-red-100 text-red-800'
  }
  return colorMap[color] || 'bg-neutral-100 text-neutral-800'
})

const formatDelta = computed(() => {
  if (tradingStore.sumDinv == undefined) return ''
  const change = Math.round(tradingStore.sumDinv)
  return change >= 0 ? ` (+${change})` : ` (${change})`
})

// Reactive getters from stores
const {
  pnl,
  cash,
  initialShares,
  remainingTime,
  isTradingStarted,
  currentHumanTraders,
  expectedHumanTraders
} = tradingStore

// Methods
function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

function refreshPage() {
  window.location.reload()
}

function finalizingDay() {
  if (props.traderUuid) {
    router.push({ name: 'Summary', params: { traderUuid: props.traderUuid } })
  } else {
    console.error('No trader UUID found')
    router.push({ name: 'Auth' })
  }
}

// Watchers
watch(() => remainingTime, (newValue) => {
  if (newValue === 0 && isTradingStarted.value) {
    finalizingDay()
  }
})

watch(() => isGoalAchieved.value, (newValue) => {
  if (newValue) {
    // Cancel all active orders when goal is achieved
    tradingStore.activeOrders.forEach(order => {
      tradingStore.cancelOrder(order.id)
    })
  }
})

// Lifecycle
onMounted(async () => {
  try {
    console.log('TradingDashboard mounted, props:', props)
    console.log('Auth store traderId:', authStore.traderId)
    console.log('Auth store marketId:', authStore.marketId)
    
    // Use trader ID from props first, then auth store fallback
    const traderId = props.traderUuid || authStore.traderId
    const marketId = props.marketId || authStore.marketId
    
    console.log('Final traderId:', traderId)
    console.log('Final marketId:', marketId)
    
    if (!traderId) {
      console.error('No trader ID available')
      showErrorAlert.value = true
      return
    }
    
    console.log('Initializing trading dashboard for trader:', traderId, 'market:', marketId)
    
    // Initialize trading data
    await tradingStore.fetchTraderAttributes(traderId)
    await tradingStore.fetchGameParams()
    
    // Initialize WebSocket connection
    console.log('Initializing WebSocket...')
    await tradingStore.initializeWebSocket()
    
    console.log('Trading dashboard initialized successfully')
  } catch (error) {
    console.error('Failed to initialize trading dashboard:', error)
    showErrorAlert.value = true
  }
})

onUnmounted(() => {
  // Clean up WebSocket connection
  if (tradingStore.ws) {
    tradingStore.ws.close()
  }
})
</script>

<style scoped>
/* Component-specific styles if needed */
</style>







