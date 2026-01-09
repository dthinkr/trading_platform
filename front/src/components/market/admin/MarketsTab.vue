<template>
  <div class="markets-tab">
    <!-- Active Markets Monitor -->
    <v-card elevation="1" class="mb-4">
      <v-card-title class="compact-title">
        <v-icon left color="deep-blue" size="18">mdi-monitor-dashboard</v-icon>
        Active Markets
        <v-spacer></v-spacer>
        <v-chip size="x-small" :color="activeSessions.length > 0 ? 'success' : 'grey'" variant="flat">
          {{ activeSessions.length }} active
        </v-chip>
      </v-card-title>

      <v-card-text>
        <v-data-table
          :headers="marketHeaders"
          :items="activeSessions"
          :items-per-page="5"
          density="compact"
          class="compact-table"
          no-data-text="No active markets"
        >
          <template v-slot:item.market_id="{ item }">
            <span class="market-id">{{ formatMarketId(item.market_id) }}</span>
          </template>

          <template v-slot:item.status="{ item }">
            <v-chip :color="getStatusColor(item.status)" size="x-small" variant="flat">
              {{ item.status }}
            </v-chip>
          </template>

          <template v-slot:item.member_ids="{ item }">
            <v-chip size="x-small" :color="item.member_ids?.length ? 'info' : 'grey'" variant="flat">
              {{ item.member_ids?.length || 0 }} members
            </v-chip>
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              size="x-small"
              color="primary"
              :disabled="item.status === 'active' || !item.member_ids?.length"
              @click="forceStartSession(item.market_id)"
              variant="outlined"
            >
              <v-icon size="14">mdi-play</v-icon>
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- No-Human Market Runner -->
    <v-card elevation="1">
      <v-card-title class="compact-title">
        <v-icon left color="deep-purple" size="18">mdi-robot-industrial</v-icon>
        No-Human Market Runner
      </v-card-title>

      <v-card-text>
        <v-alert type="info" density="compact" class="mb-4">
          Run markets with only AI traders. Useful for testing and data collection.
        </v-alert>

        <v-row dense>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="batchConfig.numMarkets"
              label="Number of Markets"
              type="number"
              min="1"
              max="10"
              variant="outlined"
              density="compact"
              hint="1-10 markets per batch"
              persistent-hint
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="batchConfig.startTreatment"
              label="Starting Treatment Index"
              type="number"
              min="0"
              variant="outlined"
              density="compact"
              hint="Which treatment to start from"
              persistent-hint
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row dense class="mt-2">
          <v-col cols="12" md="6">
            <v-switch
              v-model="batchConfig.parallel"
              label="Run in Parallel"
              color="primary"
              density="compact"
              hide-details
            ></v-switch>
          </v-col>
          <v-col cols="12" md="6" v-if="!batchConfig.parallel">
            <v-text-field
              v-model.number="batchConfig.delaySeconds"
              label="Delay Between Markets (s)"
              type="number"
              min="1"
              max="60"
              variant="outlined"
              density="compact"
              hide-details
            ></v-text-field>
          </v-col>
        </v-row>

        <v-btn
          color="deep-purple"
          @click="startHeadlessBatch"
          :loading="startingBatch"
          :disabled="!serverActive"
          class="mt-4"
          block
          variant="elevated"
        >
          <v-icon start>mdi-play-circle</v-icon>
          Start {{ batchConfig.numMarkets }} AI-Only Market{{ batchConfig.numMarkets > 1 ? 's' : '' }}
        </v-btn>

        <!-- Running Sessions -->
        <div v-if="runningSessions.length > 0" class="mt-4">
          <div class="section-label">Running Sessions</div>
          <v-chip
            v-for="session in runningSessions"
            :key="session"
            size="small"
            color="deep-purple"
            variant="outlined"
            class="mr-2 mb-2"
          >
            <v-icon start size="14">mdi-loading mdi-spin</v-icon>
            {{ formatSessionId(session) }}
          </v-chip>
        </div>

        <!-- Completed Sessions -->
        <div v-if="completedSessions.length > 0" class="mt-4">
          <div class="section-label">Recent Completed</div>
          <v-chip
            v-for="session in completedSessions.slice(0, 5)"
            :key="session"
            size="small"
            color="success"
            variant="outlined"
            class="mr-2 mb-2"
          >
            <v-icon start size="14">mdi-check</v-icon>
            {{ formatSessionId(session) }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>
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
  { title: '', key: 'actions', sortable: false, width: '60px' },
]

let pollingInterval = null

const formatMarketId = (id) => {
  if (!id) return '-'
  if (id.length > 20) return '...' + id.slice(-16)
  return id
}

const formatSessionId = (id) => {
  if (!id) return '-'
  // Extract just the timestamp and short hash
  const parts = id.split('_')
  if (parts.length >= 2) {
    return `${parts[0].slice(-6)}_${parts[1].slice(0, 6)}`
  }
  return id.slice(-12)
}

const getStatusColor = (status) => {
  const colors = {
    pending: 'warning',
    active: 'success',
    completed: 'grey',
  }
  return colors[status] || 'grey'
}

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`)
    activeSessions.value = response.data || []
    
    // Track running headless sessions
    const headless = activeSessions.value
      .filter(s => s.market_id?.includes('SESSION_'))
      .map(s => {
        const match = s.market_id.match(/SESSION_(\d+_[a-f0-9]+)/)
        return match ? match[1] : null
      })
      .filter(Boolean)
    
    // Update running sessions (remove completed ones)
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
    
    // Refresh sessions
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

.compact-title {
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.75rem !important;
  background: rgba(248, 250, 252, 0.8);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  display: flex;
  align-items: center;
  color: #1e293b !important;
}

.compact-table {
  font-size: 0.85rem;
}

.market-id {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}
</style>
