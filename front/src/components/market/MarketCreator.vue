<template>
  <div class="min-h-screen bg-neutral-50">
    <!-- Skip link for accessibility -->
    <a href="#admin-content" class="skip-link">Skip to admin content</a>
    
    <!-- Compact Header -->
    <header class="bg-white shadow-sm border-b border-neutral-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center h-14">
          <div class="flex items-center space-x-3">
            <div class="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center">
              <CogIcon class="h-4 w-4 text-white" aria-hidden="true" />
            </div>
            <div>
              <h1 class="text-lg font-semibold text-neutral-900">Trading Market Configuration</h1>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Compact Main Content -->
    <main id="admin-content" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- Left Column: Configuration Forms -->
        <div class="lg:col-span-8 space-y-6">
          <!-- Configuration Form -->
          <MarketConfigForm 
            :formState="formState" 
            :formFields="formFields"
            @update:formState="updateFormState"
          />
          
          <!-- Order Throttling -->
          <OrderThrottling 
            :formState="formState"
            @update:formState="updateFormState"
          />
        </div>

        <!-- Right Column: Monitoring & Settings -->
        <div class="lg:col-span-4 space-y-6">
          <!-- Active Markets Monitor -->
          <ActiveMarketsMonitor />
          
          <!-- Prolific Settings -->
          <ProlificSettings />
          
          <!-- Log Files -->
          <LogFilesManager />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { 
  CogIcon
} from '@heroicons/vue/24/outline'
import axios from '@/api/axios'
import MarketConfigForm from './creator/MarketConfigForm.vue'
import OrderThrottling from './creator/OrderThrottling.vue'
import ActiveMarketsMonitor from './creator/ActiveMarketsMonitor.vue'
import ProlificSettings from './creator/ProlificSettings.vue'
import LogFilesManager from './creator/LogFilesManager.vue'

// Main state
const formState = ref({
  throttle_settings: {
    HUMAN: { order_throttle_ms: 1000, max_orders_per_window: 2 },
    NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
    MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
    SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
  }
})
const formFields = ref([])

// Update form state when child components modify it
const updateFormState = (newState) => {
  formState.value = newState
}

// Fetch initial data
const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`)
    ])

    const defaultData = defaultsResponse.data.data
    const persistentSettings = persistentSettingsResponse.data.data

    // Initialize formState
    formState.value = {}
    
    // Load the form data first
    for (const [key, value] of Object.entries(defaultData)) {
      if (key !== 'throttle_settings') {
        formState.value[key] = persistentSettings[key] || value.default
        formFields.value.push({ name: key, ...value })
      }
    }
    
    // Handle throttle settings separately
    const defaultThrottleSettings = {
      HUMAN: { order_throttle_ms: 100, max_orders_per_window: 1 },
      NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
      MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
      SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
    }
    
    formState.value.throttle_settings = persistentSettings.throttle_settings || defaultThrottleSettings
  } catch (error) {
    console.error('Error fetching data:', error)
  }
}

// Lifecycle
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.market-creator {
  zoom: 90%;
  -moz-transform: scale(0.9);
  -webkit-transform: scale(0.9);
  transform: scale(0.9);
  -moz-transform-origin: 0 0;
  -webkit-transform-origin: 0 0;
  transform-origin: 0 0;
}

.headline {
  font-size: 1.35rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.subtitle-1 {
  font-size: 1rem;
  font-weight: 500;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.deep-blue {
  color: #1a237e !important;
}

.custom-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: 0.5px !important;
  font-family: 'Inter', sans-serif !important;
}
</style>
