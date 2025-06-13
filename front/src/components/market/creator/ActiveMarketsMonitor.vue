<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-center space-x-2">
        <ComputerDesktopIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
        <h2 class="text-base font-semibold text-neutral-900">Active Markets</h2>
      </div>
    </div>
    
    <div class="card-body p-4">
      <div v-if="activeSessions.length === 0" class="text-center py-6">
        <ComputerDesktopIcon class="h-8 w-8 text-neutral-400 mx-auto mb-2" />
        <p class="text-xs text-neutral-500">No active sessions</p>
      </div>
      
      <div v-else class="space-y-2">
        <div
          v-for="session in activeSessions.slice(0, 5)"
          :key="session.market_id"
          class="border border-neutral-200 rounded p-2 hover:bg-neutral-25"
        >
          <div class="flex items-center justify-between mb-1">
            <div class="text-xs font-medium text-neutral-900 truncate mr-2">
              {{ session.market_id }}
            </div>
            <span :class="[
              'inline-flex px-1.5 py-0.5 text-xs font-semibold rounded-full',
              getStatusColor(session.status)
            ]">
              {{ session.status }}
            </span>
          </div>
          
          <div class="flex items-center justify-between text-xs text-neutral-600">
            <div class="flex items-center">
              <UsersIcon class="h-3 w-3 mr-1" aria-hidden="true" />
              <span>{{ session.member_ids?.length || 0 }} members</span>
            </div>
            <button
              v-if="session.status !== 'active' && session.member_ids?.length"
              @click="forceStartSession(session.market_id)"
              class="text-blue-600 hover:text-blue-800 text-xs px-2 py-0.5 rounded border border-blue-200 hover:bg-blue-50"
            >
              Start
            </button>
          </div>
          
          <div v-if="session.started_at" class="text-xs text-neutral-500 mt-1">
            {{ new Date(session.started_at).toLocaleTimeString() }}
          </div>
        </div>
        
        <div v-if="activeSessions.length > 5" class="text-xs text-neutral-500 text-center pt-2 border-t border-neutral-200">
          +{{ activeSessions.length - 5 }} more sessions
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  ComputerDesktopIcon, 
  UsersIcon
} from '@heroicons/vue/24/outline'
import axios from '@/api/axios'

const activeSessions = ref([])
let sessionPollingInterval

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`)
    activeSessions.value = response.data || []
  } catch (error) {
    console.error("Failed to fetch sessions:", error)
  }
}

const forceStartSession = async (marketId) => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}sessions/${marketId}/force-start`)
    console.log('Session started successfully')
    await fetchActiveSessions()
  } catch (error) {
    console.error('Error starting session:', error.response?.data?.detail || 'Unknown error')
  }
}

const getStatusColor = (status) => {
  const colors = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'active': 'bg-green-100 text-green-800',
    'completed': 'bg-neutral-100 text-neutral-800'
  }
  return colors[status] || 'bg-neutral-100 text-neutral-800'
}

onMounted(() => {
  fetchActiveSessions()
  // Poll for session updates every 10 seconds (less frequent)
  sessionPollingInterval = setInterval(fetchActiveSessions, 10000)
})

onUnmounted(() => {
  if (sessionPollingInterval) {
    clearInterval(sessionPollingInterval)
  }
})
</script>
