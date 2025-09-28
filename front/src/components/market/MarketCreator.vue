<template>
  <div class="admin-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <div class="header-info">
          <div>
            <h1 class="dashboard-title">
              <v-icon size="28" color="#667eea">mdi-view-dashboard</v-icon>
              Trading Platform Admin
            </h1>
            <p class="dashboard-subtitle">Market Configuration & Management</p>
          </div>
        </div>
        <div class="header-status">
          <div class="status-chip" :class="serverActive ? 'status-online' : 'status-offline'">
            <div class="status-indicator" :class="serverActive ? 'online' : 'offline'"></div>
            <span class="status-text">{{ serverActive ? 'Server Online' : 'Server Offline' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <v-container fluid class="dashboard-content">
      <v-row dense>
        <!-- Column 1 - Market Configuration -->
        <v-col cols="12" lg="7" xl="8" class="pr-3">
          <MarketConfigForm
            :formState="formState"
            :formFields="formFields"
            :serverActive="serverActive"
            @update:formState="updateFormState"
          />
        </v-col>

        <!-- Column 2 - Monitoring, Settings & Export -->
        <v-col cols="12" lg="5" xl="4" class="pl-1">
          <div class="column-container">
            <div class="mb-3">
              <ActiveMarketsMonitor />
            </div>
            <div class="mb-3">
              <ProlificSettings />
            </div>
            <div>
              <LogFilesManager />
            </div>
          </div>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/api/axios'
import MarketConfigForm from './creator/MarketConfigForm.vue'
// OrderThrottling is now integrated into MarketConfigForm
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
.admin-dashboard {
  min-height: 100vh;
  background: #f3f4f6;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header Styles */
.dashboard-header {
  background: white;
  color: #1e293b;
  padding: 1rem 2rem;
  box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.header-info {
  display: flex;
  align-items: center;
}

.dashboard-title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dashboard-subtitle {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.7;
  font-weight: 500;
  margin-top: 0.25rem;
  color: #6b7280;
}

.header-status {
  display: flex;
  align-items: center;
}

/* Content Styles */
.dashboard-content {
  padding: 0.75rem !important;
  max-width: 1600px;
  margin: 0 auto;
}

/* Column Styles */
.column-container {
  position: sticky;
  top: 100px;
  height: fit-content;
}

.sidebar-card-title {
  font-size: 1rem !important;
  font-weight: 600 !important;
  padding: 0.75rem 1rem !important;
  background: rgba(248, 250, 252, 0.8);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  color: #334155 !important;
  backdrop-filter: blur(4px);
}

/* Removed tab styling since we no longer use tabs */

/* Card Improvements */
:deep(.v-card) {
  border-radius: 12px !important;
  border: 1px solid rgba(203, 213, 225, 0.3);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}

:deep(.v-card:hover) {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.9);
}

:deep(.v-card-title) {
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  color: #1e293b !important;
  padding: 0.5rem 0.75rem 0.25rem !important;
}

:deep(.v-card-text) {
  color: #475569 !important;
  padding: 0.5rem 0.75rem !important;
}

/* Button Improvements */
:deep(.v-btn) {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: 0.025em !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}

:deep(.v-btn--elevated) {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

:deep(.v-btn--elevated:hover) {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2) !important;
  transform: translateY(-1px);
}

/* Status Chip Styling */
.status-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(248, 250, 252, 0.8);
  border: 1px solid rgba(203, 213, 225, 0.5);
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.status-chip.status-online {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.3);
  color: #065f46;
}

.status-chip.status-offline {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #991b1b;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-indicator.online {
  background: #10b981;
}

.status-indicator.offline {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Data Table Improvements */
:deep(.v-data-table) {
  border-radius: 12px !important;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

:deep(.v-data-table-header) {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

:deep(.v-data-table-header th) {
  font-weight: 600 !important;
  color: #374151 !important;
  font-size: 0.85rem !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase;
}

/* Form Field Improvements */
:deep(.v-text-field) {
  transition: all 0.2s ease;
}

:deep(.v-text-field .v-field) {
  border-radius: 8px !important;
}

:deep(.v-text-field .v-field--focused) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

/* Responsive Design */
@media (max-width: 1264px) {
  .dashboard-content {
    padding: 0.5rem !important;
  }
  
  .header-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .column-container {
    position: static;
    margin-top: 0.5rem;
  }

  /* Stack columns on medium screens */
  .v-col[class*="lg-"] {
    flex: 0 0 100% !important;
    max-width: 100% !important;
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    padding: 1rem;
  }
  
  .dashboard-title {
    font-size: 1.5rem;
  }
  
  .dashboard-content {
    padding: 0.25rem !important;
  }
}

/* Custom scrollbar */
:deep(*::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
}

:deep(*::-webkit-scrollbar-track) {
  background: #f1f5f9;
  border-radius: 3px;
}

:deep(*::-webkit-scrollbar-thumb) {
  background: #cbd5e1;
  border-radius: 3px;
}

:deep(*::-webkit-scrollbar-thumb:hover) {
  background: #94a3b8;
}
</style>
