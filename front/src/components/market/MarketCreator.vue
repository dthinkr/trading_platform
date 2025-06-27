<template>
  <div class="market-creator">
    <v-container fluid class="pa-4">
      <v-row class="mb-4">
        <!-- Configuration Form -->
        <v-col cols="12">
          <MarketConfigForm
            :formState="formState"
            :formFields="formFields"
            :serverActive="serverActive"
            @update:formState="updateFormState"
          />
        </v-col>

        <!-- Order Throttling -->
        <v-col cols="12">
          <OrderThrottling :formState="formState" @update:formState="updateFormState" />
        </v-col>

        <!-- Market Monitor -->
        <v-col cols="12" md="8">
          <ActiveMarketsMonitor />
        </v-col>

        <!-- Prolific Settings -->
        <v-col cols="12" md="4">
          <ProlificSettings class="mb-4" />
        </v-col>

        <!-- Log Files -->
        <v-col cols="12" md="4">
          <LogFilesManager class="mb-4" />
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
    SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 },
  },
})
const formFields = ref([])
const serverActive = ref(false)

// Update form state when child components modify it
const updateFormState = (newState) => {
  formState.value = newState
}

// Fetch initial data
const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`),
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
      SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    }

    formState.value.throttle_settings =
      persistentSettings.throttle_settings || defaultThrottleSettings
    serverActive.value = true
  } catch (error) {
    serverActive.value = false
    console.error('Failed to fetch data:', error)
  }
}

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
