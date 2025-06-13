<template>
  <div class="market-creator min-h-screen bg-gray-50 p-4">
    <div class="max-w-7xl mx-auto">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Trading Market Configuration</h1>
        <p class="text-gray-600">Configure and monitor your trading markets</p>
      </div>
      
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Configuration Form -->
        <div class="lg:col-span-3">
          <MarketConfigForm 
            :formState="formState" 
            :formFields="formFields" 
            :serverActive="serverActive"
            @update:formState="updateFormState"
          />
        </div>
        
        <!-- Order Throttling -->
        <div class="lg:col-span-3">
          <OrderThrottling 
            :formState="formState"
            @update:formState="updateFormState"
          />
        </div>

        <!-- Market Monitor -->
        <div class="lg:col-span-2">
          <ActiveMarketsMonitor />
        </div>

        <!-- Prolific Settings -->
        <div class="lg:col-span-1">
          <ProlificSettings class="mb-6" />
        </div>
        
        <!-- Log Files -->
        <div class="lg:col-span-1">
          <LogFilesManager />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '@/api/axios';
import MarketConfigForm from './creator/MarketConfigForm.vue';
import OrderThrottling from './creator/OrderThrottling.vue';
import ActiveMarketsMonitor from './creator/ActiveMarketsMonitor.vue';
import ProlificSettings from './creator/ProlificSettings.vue';
import LogFilesManager from './creator/LogFilesManager.vue';

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
});
const formFields = ref([]);
const serverActive = ref(false);

// Update form state when child components modify it
const updateFormState = (newState) => {
  formState.value = newState;
};

// Fetch initial data
const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`)
    ]);

    const defaultData = defaultsResponse.data.data;
    const persistentSettings = persistentSettingsResponse.data.data;

    // Initialize formState
    formState.value = {};
    
    // Load the form data first
    for (const [key, value] of Object.entries(defaultData)) {
      if (key !== 'throttle_settings') {
        formState.value[key] = persistentSettings[key] || value.default;
        formFields.value.push({ name: key, ...value });
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
    };
    
    formState.value.throttle_settings = persistentSettings.throttle_settings || defaultThrottleSettings;
    serverActive.value = true;
  } catch (error) {
    serverActive.value = false;
    console.error("Failed to fetch data:", error);
  }
};

onMounted(() => {
  fetchData();
});
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
