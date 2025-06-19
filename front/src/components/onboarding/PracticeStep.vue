<template>
  <div class="space-y-6">
    <!-- Practice header -->
    <div class="text-center">
      <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <PuzzlePieceIcon class="h-8 w-8 text-purple-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Practice Session
      </h3>
      <p class="text-lg text-neutral-600">
        Familiarize yourself with the trading platform
      </p>
    </div>

    <!-- Practice instructions -->
    <div class="bg-purple-50 rounded-lg p-6 border border-purple-200">
      <h4 class="font-semibold text-purple-900 mb-3 flex items-center">
        <InformationCircleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Practice Instructions
      </h4>
      <div class="space-y-2 text-purple-800 text-sm">
        <p>This is a practice environment to help you familiarize yourself with the trading platform before the actual markets begin.</p>
        <ul class="list-disc list-inside space-y-1">
          <li>Try placing both buy and sell orders at different price levels</li>
          <li>Experiment with the interface and understand how orders work</li>
          <li>Practice cancelling orders before they execute</li>
          <li>Get comfortable with the order book and price movements</li>
          <li>This is practice only - no real money or shares are involved</li>
        </ul>
      </div>
    </div>

    <!-- Practice trading interface -->
    <div class="grid gap-6 lg:grid-cols-3">
      <!-- Mock Order Book -->
      <div class="card">
        <div class="card-header">
          <h4 class="text-lg font-semibold text-neutral-900 flex items-center">
            <BookOpenIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
            Order Book
          </h4>
        </div>
        <div class="card-body">
          <div class="space-y-2">
            <!-- Asks -->
            <div class="text-center text-xs text-neutral-500 mb-2">Sellers (Asks)</div>
            <div v-for="ask in mockOrderBook.asks" :key="ask.price" 
                 class="flex justify-between items-center p-2 bg-red-50 rounded text-sm">
              <span class="text-red-700">${{ ask.price }}</span>
              <span class="text-neutral-600">{{ ask.volume }}</span>
            </div>
            
            <!-- Spread -->
            <div class="border-t border-b border-neutral-200 py-2 text-center">
              <span class="text-xs text-neutral-500">
                Spread: ${{ spread }}
              </span>
            </div>
            
            <!-- Bids -->
            <div v-for="bid in mockOrderBook.bids" :key="bid.price"
                 class="flex justify-between items-center p-2 bg-blue-50 rounded text-sm">
              <span class="text-blue-700">${{ bid.price }}</span>
              <span class="text-neutral-600">{{ bid.volume }}</span>
            </div>
            <div class="text-center text-xs text-neutral-500 mt-2">Buyers (Bids)</div>
          </div>
        </div>
      </div>

      <!-- Practice Order Form -->
      <div class="card">
        <div class="card-header">
          <h4 class="text-lg font-semibold text-neutral-900 flex items-center">
            <CurrencyDollarIcon class="h-5 w-5 mr-2 text-green-600" aria-hidden="true" />
            Place Practice Order
          </h4>
        </div>
        <div class="card-body space-y-4">
          <!-- Order Type -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-2">Order Type</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                @click="practiceOrder.type = 'BUY'"
                :class="[
                  'btn text-sm py-2',
                  practiceOrder.type === 'BUY' ? 'btn-primary' : 'btn-outline'
                ]"
              >
                Buy
              </button>
              <button
                @click="practiceOrder.type = 'SELL'"
                :class="[
                  'btn text-sm py-2', 
                  practiceOrder.type === 'SELL' ? 'btn-danger' : 'btn-outline'
                ]"
              >
                Sell
              </button>
            </div>
          </div>

          <!-- Quick Price Selection -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-2">Quick Prices</label>
            <div class="grid grid-cols-3 gap-1">
              <button
                v-for="price in quickPrices"
                :key="price"
                @click="practiceOrder.price = price"
                class="btn btn-outline text-xs py-1"
              >
                ${{ price }}
              </button>
            </div>
          </div>

          <!-- Price Input -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1">Price</label>
            <input
              v-model.number="practiceOrder.price"
              type="number"
              min="95"
              max="110"
              step="1"
              class="input"
              placeholder="Enter price"
            />
          </div>

          <!-- Quantity -->
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1">Quantity</label>
            <input
              v-model.number="practiceOrder.quantity"
              type="number"
              min="1"
              max="10"
              step="1"
              class="input"
              placeholder="Enter quantity"
            />
          </div>

          <!-- Submit Button -->
          <button
            @click="placePracticeOrder"
            :disabled="!canPlaceOrder"
            :class="[
              'btn w-full',
              practiceOrder.type === 'BUY' ? 'btn-primary' : 'btn-danger',
              !canPlaceOrder && 'opacity-50 cursor-not-allowed'
            ]"
          >
            Place {{ practiceOrder.type }} Order
          </button>
        </div>
      </div>

      <!-- Practice Portfolio & Orders -->
      <div class="space-y-4">
        <!-- Portfolio -->
        <div class="card">
          <div class="card-header">
            <h4 class="text-lg font-semibold text-neutral-900 flex items-center">
              <WalletIcon class="h-5 w-5 mr-2 text-orange-600" aria-hidden="true" />
              Practice Portfolio
            </h4>
          </div>
          <div class="card-body">
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span>Cash:</span>
                <span class="font-medium">${{ practicePortfolio.cash.toLocaleString() }}</span>
              </div>
              <div class="flex justify-between">
                <span>Shares:</span>
                <span class="font-medium">{{ practicePortfolio.shares }}</span>
              </div>
              <div class="flex justify-between">
                <span>P&L:</span>
                <span :class="[
                  'font-medium',
                  practicePortfolio.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                ]">
                  {{ practicePortfolio.pnl >= 0 ? '+' : '' }}${{ practicePortfolio.pnl }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Active Orders -->
        <div class="card">
          <div class="card-header">
            <h4 class="text-lg font-semibold text-neutral-900 flex items-center">
              <ClipboardDocumentListIcon class="h-5 w-5 mr-2 text-indigo-600" aria-hidden="true" />
              Active Orders
            </h4>
          </div>
          <div class="card-body">
            <div v-if="practiceOrders.length === 0" class="text-sm text-neutral-500 text-center py-4">
              No active orders
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="order in practiceOrders"
                :key="order.id"
                class="flex justify-between items-center p-2 bg-neutral-50 rounded text-sm"
              >
                <div>
                  <span :class="order.type === 'BUY' ? 'text-blue-600' : 'text-red-600'">
                    {{ order.type }}
                  </span>
                  <span class="ml-2">${{ order.price }} × {{ order.quantity }}</span>
                </div>
                <button
                  @click="cancelPracticeOrder(order.id)"
                  class="btn btn-ghost text-xs p-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Practice progress -->
    <div class="bg-green-50 rounded-lg p-6 border border-green-200">
      <h4 class="font-semibold text-green-900 mb-3 flex items-center">
        <CheckCircleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Practice Progress
      </h4>
      <div class="space-y-2">
        <div class="flex items-center justify-between text-sm">
          <span>Orders placed:</span>
          <span class="font-medium">{{ practiceStats.ordersPlaced }}</span>
        </div>
        <div class="flex items-center justify-between text-sm">
          <span>Orders cancelled:</span>
          <span class="font-medium">{{ practiceStats.ordersCancelled }}</span>
        </div>
        <div v-if="practiceStats.ordersPlaced >= 2" class="mt-4">
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm font-medium">Great! You've practiced enough to proceed.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Completion -->
    <div class="flex items-center justify-center">
      <label class="flex items-center space-x-3 cursor-pointer">
        <input
          type="checkbox"
          v-model="completed"
          @change="$emit('update:completed', completed)"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-neutral-300 rounded"
        />
        <span class="text-sm text-neutral-700">
          I have practiced placing orders and feel comfortable with the interface
        </span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  PuzzlePieceIcon,
  InformationCircleIcon,
  BookOpenIcon,
  CurrencyDollarIcon,
  WalletIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  completed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:completed'])

// Practice state
const completed = ref(props.completed)
const practiceOrder = ref({
  type: 'BUY',
  price: 100,
  quantity: 1
})

const practicePortfolio = ref({
  cash: 10000,
  shares: 50,
  pnl: 0
})

const practiceOrders = ref([])
const practiceStats = ref({
  ordersPlaced: 0,
  ordersCancelled: 0
})

// Mock data
const mockOrderBook = ref({
  asks: [
    { price: 105, volume: 10 },
    { price: 104, volume: 15 },
    { price: 103, volume: 8 }
  ],
  bids: [
    { price: 102, volume: 12 },
    { price: 101, volume: 20 },
    { price: 100, volume: 15 }
  ]
})

// Computed properties
const spread = computed(() => {
  const bestAsk = Math.min(...mockOrderBook.value.asks.map(a => a.price))
  const bestBid = Math.max(...mockOrderBook.value.bids.map(b => b.price))
  return bestAsk - bestBid
})

const quickPrices = computed(() => {
  if (practiceOrder.value.type === 'BUY') {
    return mockOrderBook.value.asks.slice(0, 3).map(a => a.price)
  } else {
    return mockOrderBook.value.bids.slice(0, 3).map(b => b.price)
  }
})

const canPlaceOrder = computed(() => {
  return practiceOrder.value.price > 0 && practiceOrder.value.quantity > 0
})

// Methods
function placePracticeOrder() {
  if (!canPlaceOrder.value) return

  const newOrder = {
    id: Date.now(),
    type: practiceOrder.value.type,
    price: practiceOrder.value.price,
    quantity: practiceOrder.value.quantity,
    timestamp: new Date()
  }

  practiceOrders.value.push(newOrder)
  practiceStats.value.ordersPlaced++

  // Reset form
  practiceOrder.value.quantity = 1
  
  // Auto-complete after 2 orders
  if (practiceStats.value.ordersPlaced >= 2) {
    setTimeout(() => {
      completed.value = true
      emit('update:completed', true)
    }, 1000)
  }
}

function cancelPracticeOrder(orderId) {
  practiceOrders.value = practiceOrders.value.filter(order => order.id !== orderId)
  practiceStats.value.ordersCancelled++
}
</script> 