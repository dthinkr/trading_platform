<template>
  <div class="markets-tab">
    <!-- Active Markets Monitor -->
    <section class="tp-card mb-4">
      <header class="tp-card-header">
        <h2 class="tp-card-title">Active Markets</h2>
        <span class="tp-badge" :class="activeSessions.length > 0 ? 'tp-badge-success' : ''">
          {{ activeSessions.length }} active
        </span>
      </header>

      <div class="tp-card-body">
        <v-data-table
          :headers="marketHeaders"
          :items="activeSessions"
          :items-per-page="5"
          density="compact"
          no-data-text="No active markets"
        >
          <template v-slot:item.market_id="{ item }">
            <span class="font-mono text-sm text-muted">{{ formatMarketId(item.market_id) }}</span>
          </template>

          <template v-slot:item.status="{ item }">
            <span class="tp-badge" :class="getStatusBadgeClass(item.status)">
              {{ item.status }}
            </span>
          </template>

          <template v-slot:item.member_ids="{ item }">
            <span class="tp-badge" :class="item.member_ids?.length ? 'tp-badge-info' : ''">
              {{ item.member_ids?.length || 0 }} members
            </span>
          </template>

          <template v-slot:item.actions="{ item }">
            <button
              class="tp-btn tp-btn-sm tp-btn-secondary"
              :disabled="item.status === 'active' || !item.member_ids?.length"
              @click="forceStartSession(item.market_id)"
            >
              Start
            </button>
          </template>
        </v-data-table>
      </div>
    </section>

    <!-- No-Human Market Runner -->
    <section class="tp-card">
      <header class="tp-card-header">
        <h2 class="tp-card-title">No-Human Market Runner</h2>
      </header>

      <div class="tp-card-body">
        <p class="text-sm text-secondary mb-4">
          Run markets with only AI traders. Useful for testing and data collection.
        </p>

        <div class="config-grid mb-4">
          <v-text-field
            v-model.number="batchConfig.numMarkets"
            label="Number of Markets"
            type="number"
            min="1"
            max="10"
            hint="1-10 markets per batch"
            persistent-hint
          />
          <v-text-field
            v-model.number="batchConfig.startTreatment"
            label="Starting Treatment Index"
            type="number"
            min="0"
            hint="Which treatment to start from"
            persistent-hint
          />
        </div>

        <div class="config-row mb-4">
          <v-switch
            v-model="batchConfig.parallel"
            label="Run in Parallel"
            color="primary"
            hide-details
          />
          <v-text-field
            v-if="!batchConfig.parallel"
            v-model.number="batchConfig.delaySeconds"
            label="Delay Between Markets (s)"
            type="number"
            min="1"
            max="60"
            hide-details
            style="max-width: 200px"
          />
        </div>

        <button
          class="tp-btn tp-btn-primary"
          style="width: 100%"
          @click="startHeadlessBatch"
          :disabled="!serverActive || startingBatch"
        >
          {{ startingBatch ? 'Starting...' : `Start ${batchConfig.numMarkets} AI-Only Market${batchConfig.numMarkets > 1 ? 's' : ''}` }}
        </button>

        <!-- Running Sessions -->
        <div v-if="runningSessions.length > 0" class="mt-4">
          <span class="tp-label">Running Sessions</span>
          <div class="session-chips">
            <span
              v-for="session in runningSessions"
              :key="session"
              class="tp-badge tp-badge-info"
            >
              {{ formatSessionId(session) }}
            </span>
          </div>
        </div>

        <!-- Completed Sessions -->
        <div v-if="completedSessions.length > 0" class="mt-4">
          <span class="tp-label">Recent Completed</span>
          <div class="session-chips">
            <span
              v-for="session in completedSessions.slice(0, 5)"
              :key="session"
              class="tp-badge tp-badge-success"
            >
              {{ formatSessionId(session) }}
            </span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/api/axios'
import { useUIStore } from '@/store/ui'

const props = defineProps({
  serverActive: { type: Boolean, required: true },
})

const uiStore = useUIStore()

const activeSessions = ref([])
const runningSessions = ref([])
const completedSessions = ref([])
const startingBatch = ref(false)

const batchConfig = ref({
  numMarkets: 3,
  startTreatment: 0,
  parallel: true,
  delaySeconds: 5,
})

const marketHeaders = [
  { title: 'Market ID', key: 'market_id' },
  { title: 'Status', key: 'status' },
  { title: 'Members', key: 'member_ids' },
  { title: '', key: 'actions', sortable: false, width: '80px' },
]

let pollingInterval = null

const formatMarketId = (id) => {
  if (!id) return '-'
  if (id.length > 20) return '...' + id.slice(-16)
  return id
}

const formatSessionId = (id) => {
  if (!id) return '-'
  const parts = id.split('_')
  if (parts.length >= 2) {
    return `${parts[0].slice(-6)}_${parts[1].slice(0, 6)}`
  }
  return id.slice(-12)
}

const getStatusBadgeClass = (status) => {
  const classes = {
    pending: 'tp-badge-warning',
    active: 'tp-badge-success',
    completed: '',
  }
  return classes[status] || ''
}

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`)
    activeSessions.value = response.data || []
    
    runningSessions.value = runningSessions.value.filter(s => 
      activeSessions.value.some(a => a.market_id?.includes(s))
    )
  } catch (error) {
    console.error('Failed to fetch sessions:', error)
  }
}

const forceStartSession = async (marketId) => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}sessions/${marketId}/force-start`)
    uiStore.showSuccess('Session started')
    await fetchActiveSessions()
  } catch (error) {
    uiStore.showError(error.response?.data?.detail || 'Error starting session')
  }
}

const startHeadlessBatch = async () => {
  startingBatch.value = true
  try {
    const params = new URLSearchParams({
      num_markets: batchConfig.value.numMarkets,
      start_treatment: batchConfig.value.startTreatment,
      parallel: batchConfig.value.parallel,
      delay_seconds: batchConfig.value.delaySeconds,
    })
    
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/run_headless_batch?${params}`)
    
    if (response.data.session_id) {
      runningSessions.value.push(response.data.session_id)
      uiStore.showSuccess(`Started batch: ${formatSessionId(response.data.session_id)}`)
    }
    
    await fetchActiveSessions()
  } catch (error) {
    uiStore.showError(error.response?.data?.detail || 'Failed to start batch')
  } finally {
    startingBatch.value = false
  }
}

onMounted(() => {
  fetchActiveSessions()
  pollingInterval = setInterval(fetchActiveSessions, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
</script>

<style scoped>
.markets-tab {
  max-width: 900px;
}

.mb-4 { margin-bottom: var(--space-4); }
.mt-4 { margin-top: var(--space-4); }

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.config-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

/* Session Chips */
.session-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

@media (max-width: 600px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .config-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
