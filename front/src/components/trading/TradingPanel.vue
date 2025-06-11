<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <CurrencyDollarIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Place Order
      </h3>
    </div>
    <div class="card-body space-y-4">
      <!-- Order Type Selection -->
      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-2">
          Order Type
        </label>
        <div class="grid grid-cols-2 gap-2">
          <button
            @click="orderType = 'BID'"
            :class="[
              'btn text-sm py-2',
              orderType === 'BID' 
                ? 'btn-primary' 
                : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
            ]"
          >
            <ArrowUpIcon class="h-4 w-4 mr-1" />
            Buy
          </button>
          <button
            @click="orderType = 'ASK'"
            :class="[
              'btn text-sm py-2',
              orderType === 'ASK' 
                ? 'btn-danger' 
                : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
            ]"
          >
            <ArrowDownIcon class="h-4 w-4 mr-1" />
            Sell
          </button>
        </div>
      </div>

      <!-- Quick Price Selection -->
      <div v-if="quickPrices.length > 0">
        <label class="block text-sm font-medium text-neutral-700 mb-2">
          Quick Price Select
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="priceLevel in quickPrices"
            :key="priceLevel.price"
            @click="price = priceLevel.price"
            :class="[
              'btn text-xs py-1.5',
              orderType === 'BID' ? 'btn-outline-primary' : 'btn-outline-danger'
            ]"
          >
            {{ formatPrice(priceLevel.price) }}
            <span class="text-xs text-neutral-500 ml-1">
              ({{ priceLevel.volume }})
            </span>
          </button>
        </div>
      </div>

      <!-- Price Input -->
      <div>
        <label for="price" class="block text-sm font-medium text-neutral-700 mb-1">
          Price
        </label>
        <div class="relative">
          <input
            id="price"
            v-model.number="price"
            type="number"
            :min="gameParams.min_price || 1"
            :max="gameParams.max_price || 1000"
            :step="gameParams.step || 1"
            class="input pr-12"
            :class="{ 'border-red-300 focus:border-red-500': errors.price }"
            placeholder="Enter price"
          />
          <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <span class="text-neutral-500 text-sm">$</span>
          </div>
        </div>
        <p v-if="errors.price" class="mt-1 text-sm text-red-600">
          {{ errors.price }}
        </p>
        <p v-if="priceValidation" class="mt-1 text-xs text-neutral-500">
          {{ priceValidation }}
        </p>
      </div>

      <!-- Quantity Input -->
      <div>
        <label for="quantity" class="block text-sm font-medium text-neutral-700 mb-1">
          Quantity
        </label>
        <input
          id="quantity"
          v-model.number="quantity"
          type="number"
          min="1"
          :max="maxQuantity"
          step="1"
          class="input"
          :class="{ 'border-red-300 focus:border-red-500': errors.quantity }"
          placeholder="Number of shares"
        />
        <p v-if="errors.quantity" class="mt-1 text-sm text-red-600">
          {{ errors.quantity }}
        </p>
        <p v-if="maxQuantity" class="mt-1 text-xs text-neutral-500">
          Maximum available: {{ maxQuantity }} shares
        </p>
      </div>

      <!-- Order Summary -->
      <div v-if="orderTotal && !errors.price && !errors.quantity" 
           class="p-3 bg-neutral-50 rounded-lg border">
        <div class="flex justify-between items-center text-sm">
          <span class="text-neutral-600">Total Value:</span>
          <span class="font-semibold text-neutral-900">
            ${{ formatPrice(orderTotal) }}
          </span>
        </div>
        <div v-if="orderType === 'BID' && cash < orderTotal" 
             class="mt-2 text-xs text-red-600">
          Insufficient cash (Available: ${{ formatPrice(cash) }})
        </div>
        <div v-if="orderType === 'ASK' && shares < quantity" 
             class="mt-2 text-xs text-red-600">
          Insufficient shares (Available: {{ shares }})
        </div>
      </div>

      <!-- Submit Button -->
      <button
        @click="submitOrder"
        :disabled="!canSubmitOrder || isSubmitting"
        :class="[
          'btn w-full py-3 font-semibold flex items-center justify-center',
          orderType === 'BID' ? 'btn-primary' : 'btn-danger',
          (!canSubmitOrder || isSubmitting) && 'opacity-50 cursor-not-allowed'
        ]"
      >
        <div v-if="isSubmitting" class="spinner h-4 w-4 mr-2"></div>
        <template v-else>
          <component 
            :is="orderType === 'BID' ? ArrowUpIcon : ArrowDownIcon" 
            class="h-4 w-4 mr-2" 
          />
          {{ orderType === 'BID' ? 'Place Buy Order' : 'Place Sell Order' }}
        </template>
      </button>

      <!-- Error Message -->
      <div v-if="submitError" class="p-3 bg-red-50 border border-red-200 rounded-lg">
        <div class="flex items-center">
          <ExclamationTriangleIcon class="h-5 w-5 text-red-400 mr-2" />
          <span class="text-sm text-red-800">{{ submitError }}</span>
        </div>
      </div>

      <!-- Success Message -->
      <div v-if="submitSuccess" class="p-3 bg-green-50 border border-green-200 rounded-lg">
        <div class="flex items-center">
          <CheckCircleIcon class="h-5 w-5 text-green-400 mr-2" />
          <span class="text-sm text-green-800">Order placed successfully!</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { 
  CurrencyDollarIcon, 
  ArrowUpIcon, 
  ArrowDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'

const tradingStore = useTradingStore()

// Form state
const orderType = ref('BID')
const price = ref('')
const quantity = ref(1)
const isSubmitting = ref(false)
const submitError = ref('')
const submitSuccess = ref(false)

// Computed properties
const orderBook = computed(() => tradingStore.orderBook)
const cash = computed(() => tradingStore.cash)
const shares = computed(() => tradingStore.shares)
const gameParams = computed(() => tradingStore.gameParams)
const midPoint = computed(() => tradingStore.midPoint)

const quickPrices = computed(() => {
  const book = orderBook.value
  if (orderType.value === 'BID' && book.asks?.length > 0) {
    // Show best ask prices for buying
    return book.asks.slice(0, 3).map(ask => ({
      price: ask.x,
      volume: ask.y
    }))
  } else if (orderType.value === 'ASK' && book.bids?.length > 0) {
    // Show best bid prices for selling
    return book.bids.slice(0, 3).map(bid => ({
      price: bid.x,
      volume: bid.y
    }))
  }
  return []
})

const maxQuantity = computed(() => {
  if (orderType.value === 'ASK') {
    return shares.value
  }
  if (price.value && orderType.value === 'BID') {
    return Math.floor(cash.value / price.value)
  }
  return 1000 // Default maximum
})

const orderTotal = computed(() => {
  if (price.value && quantity.value) {
    return price.value * quantity.value
  }
  return 0
})

const errors = computed(() => {
  const errs = {}
  
  if (price.value !== '' && price.value !== null) {
    if (price.value <= 0) {
      errs.price = 'Price must be greater than 0'
    } else if (gameParams.value.min_price && price.value < gameParams.value.min_price) {
      errs.price = `Price must be at least ${gameParams.value.min_price}`
    } else if (gameParams.value.max_price && price.value > gameParams.value.max_price) {
      errs.price = `Price must not exceed ${gameParams.value.max_price}`
    } else if (gameParams.value.step && price.value % gameParams.value.step !== 0) {
      errs.price = `Price must be a multiple of ${gameParams.value.step}`
    }
  }
  
  if (quantity.value !== '' && quantity.value !== null) {
    if (quantity.value <= 0) {
      errs.quantity = 'Quantity must be greater than 0'
    } else if (quantity.value > maxQuantity.value) {
      errs.quantity = `Quantity cannot exceed ${maxQuantity.value}`
    }
  }
  
  return errs
})

const priceValidation = computed(() => {
  if (!price.value || !midPoint.value) return ''
  
  const diff = Math.abs(price.value - midPoint.value)
  const percentDiff = (diff / midPoint.value) * 100
  
  if (percentDiff > 10) {
    return `Price is ${percentDiff.toFixed(1)}% away from midpoint (${formatPrice(midPoint.value)})`
  }
  return ''
})

const canSubmitOrder = computed(() => {
  return (
    price.value > 0 &&
    quantity.value > 0 &&
    Object.keys(errors.value).length === 0 &&
    !isSubmitting.value &&
    tradingStore.isTradingStarted &&
    !tradingStore.dayOver
  )
})

// Methods
function formatPrice(value) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value)
}

async function submitOrder() {
  if (!canSubmitOrder.value) return
  
  isSubmitting.value = true
  submitError.value = ''
  submitSuccess.value = false
  
  try {
    await tradingStore.placeOrder(orderType.value, price.value, quantity.value)
    
    // Show success message
    submitSuccess.value = true
    setTimeout(() => {
      submitSuccess.value = false
    }, 3000)
    
    // Reset form
    price.value = ''
    quantity.value = 1
    
  } catch (error) {
    console.error('Order submission failed:', error)
    submitError.value = error.message || 'Failed to place order. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

// Clear error messages when form changes
watch([orderType, price, quantity], () => {
  submitError.value = ''
  submitSuccess.value = false
})
</script>

<style scoped>
/* Component-specific styles if needed */
</style> 