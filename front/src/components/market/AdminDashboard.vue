<template>
  <div class="admin-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="dashboard-title">
            <v-icon size="28" color="#667eea">mdi-view-dashboard</v-icon>
            Trading Platform Admin
          </h1>
        </div>
        <div class="header-status">
          <div class="status-chip" :class="serverActive ? 'status-online' : 'status-offline'">
            <div class="status-indicator" :class="serverActive ? 'online' : 'offline'"></div>
            <span class="status-text">{{ serverActive ? 'Connected' : 'Disconnected' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Layout: Tabs + Content + Export Panel -->
    <div class="main-layout">
      <!-- Left: Vertical Tabs -->
      <div class="tabs-sidebar">
        <v-tabs v-model="activeTab" direction="vertical" color="primary" class="vertical-tabs">
          <v-tab value="config">
            <v-icon start size="18">mdi-cog-outline</v-icon>
            Config
          </v-tab>
          <v-tab value="prompts">
            <v-icon start size="18">mdi-robot-outline</v-icon>
            AI Prompts
          </v-tab>
          <v-tab value="markets">
            <v-icon start size="18">mdi-monitor-dashboard</v-icon>
            Markets
          </v-tab>
        </v-tabs>
      </div>

      <!-- Center: Tab Content -->
      <div class="tab-content">
        <v-tabs-window v-model="activeTab">
          <!-- Config Tab -->
          <v-tabs-window-item value="config">
            <ConfigTab
              :formState="formState"
              :formFields="formFields"
              :serverActive="serverActive"
              @update:formState="updateFormState"
            />
          </v-tabs-window-item>

          <!-- AI Prompts Tab -->
          <v-tabs-window-item value="prompts">
            <AIPromptsTab :serverActive="serverActive" />
          </v-tabs-window-item>

          <!-- Markets Tab -->
          <v-tabs-window-item value="markets">
            <MarketsTab :serverActive="serverActive" />
          </v-tabs-window-item>
        </v-tabs-window>
      </div>

      <!-- Right: Data Export (Always Visible) -->
      <div class="export-sidebar">
        <LogFilesManager />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/api/axios'
import ConfigTab from './admin/ConfigTab.vue'
import AIPromptsTab from './admin/AIPromptsTab.vue'
import MarketsTab from './admin/MarketsTab.vue'
import LogFilesManager from './creator/LogFilesManager.vue'

const activeTab = ref('config')
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

const updateFormState = (newState) => {
  formState.value = newState
}

const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_base_settings`),
    ])

    const defaultData = defaultsResponse.data.data
    const persistentSettings = persistentSettingsResponse.data.data

    formState.value = {}

    for (const [key, value] of Object.entries(defaultData)) {
      if (key !== 'throttle_settings') {
        formState.value[key] = persistentSettings[key] ?? value.default
        formFields.value.push({ name: key, ...value })
      }
    }

    const defaultThrottleSettings = {
      HUMAN: { order_throttle_ms: 100, max_orders_per_window: 1 },
      NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
      MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
      SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    }

    formState.value.throttle_settings = persistentSettings.throttle_settings || defaultThrottleSettings
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
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  background: white;
  padding: 0.75rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dashboard-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
}

.status-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-online {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.status-offline {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.online {
  background: #22c55e;
  box-shadow: 0 0 6px #22c55e;
}

.status-indicator.offline {
  background: #ef4444;
}

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.tabs-sidebar {
  width: 140px;
  background: white;
  border-right: 1px solid #e5e7eb;
  padding-top: 1rem;
}

.vertical-tabs {
  width: 100%;
}

.vertical-tabs :deep(.v-tab) {
  justify-content: flex-start;
  text-transform: none;
  font-weight: 500;
  font-size: 0.85rem;
  min-height: 48px;
  padding: 0 1rem;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f3f4f6;
}

.export-sidebar {
  width: 320px;
  background: white;
  border-left: 1px solid #e5e7eb;
  padding: 1rem;
  overflow-y: auto;
}

@media (max-width: 1200px) {
  .export-sidebar {
    width: 280px;
  }
}

@media (max-width: 960px) {
  .main-layout {
    flex-direction: column;
  }
  
  .tabs-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0;
  }
  
  .vertical-tabs {
    flex-direction: row !important;
  }
  
  .export-sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid #e5e7eb;
  }
}
</style>
