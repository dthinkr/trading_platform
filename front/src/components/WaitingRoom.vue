<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
      <!-- Loading Animation -->
      <div class="mb-6">
        <div class="relative mx-auto w-16 h-16">
          <div class="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
          <div class="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
        </div>
      </div>

      <!-- Title -->
      <h1 class="text-2xl font-bold text-gray-900 mb-2">
        Waiting for Players
      </h1>
      
      <!-- Status Message -->
      <p class="text-gray-600 mb-6">
        {{ statusMessage }}
      </p>

      <!-- Player Count -->
      <div class="bg-gray-50 rounded-lg p-4 mb-6">
        <div class="flex items-center justify-center space-x-2 mb-2">
          <UserGroupIcon class="h-5 w-5 text-blue-600" />
          <span class="font-semibold text-gray-900">
            {{ currentPlayers }} / {{ requiredPlayers }} Players
          </span>
        </div>
        
        <!-- Progress Bar -->
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div 
            class="bg-blue-600 h-2 rounded-full transition-all duration-500"
            :style="{ width: `${(currentPlayers / requiredPlayers) * 100}%` }"
          ></div>
        </div>
        
        <p class="text-sm text-gray-500 mt-2">
          Waiting for {{ waitingFor }} more {{ waitingFor === 1 ? 'player' : 'players' }}
        </p>
      </div>

      <!-- Session Info -->
      <div v-if="sessionId" class="text-xs text-gray-400 mb-4">
        Session: {{ sessionId }}
      </div>

      <!-- Error Message -->
      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
        <p class="text-red-600 text-sm">{{ error }}</p>
      </div>

      <!-- Instructions -->
      <div class="text-sm text-gray-500">
        <p>Please keep this page open while we find other participants.</p>
        <p class="mt-1">The trading session will start automatically when ready.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserGroupIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const authStore = useAuthStore()

// State
const currentPlayers = ref(0)
const requiredPlayers = ref(1)
const waitingFor = ref(1)
const sessionId = ref('')
const error = ref('')
const pollInterval = ref(null)

// Computed
const statusMessage = computed(() => {
  if (currentPlayers.value === 0) {
    return 'Joining waiting room...'
  } else if (currentPlayers.value < requiredPlayers.value) {
    return 'Looking for more participants to join your session'
  } else {
    return 'Session ready! Starting trading...'
  }
})

// Methods
const joinWaitingRoom = async () => {
  try {
    error.value = ''
    const response = await authStore.joinWaitingRoom()
    
    if (response.status === 'success') {
      if (response.data.session_ready) {
        // Session is ready, redirect to trading
        console.log('Session ready, redirecting to trading...')
        await router.push('/trading')
      } else {
        // Update waiting room status
        updateStatus(response.data)
        startPolling()
      }
    } else {
      error.value = response.message || 'Failed to join waiting room'
    }
  } catch (err) {
    console.error('Error joining waiting room:', err)
    error.value = 'Failed to join waiting room. Please try again.'
  }
}

const checkStatus = async () => {
  try {
    const status = await authStore.getWaitingRoomStatus()
    
    if (status.in_waiting_room) {
      updateStatus(status)
    } else {
      // User not in waiting room, try to join
      await joinWaitingRoom()
    }
  } catch (err) {
    console.error('Error checking waiting room status:', err)
    error.value = 'Connection error. Please refresh the page.'
  }
}

const updateStatus = (data) => {
  currentPlayers.value = data.current_players || 0
  requiredPlayers.value = data.required_players || 1
  waitingFor.value = data.waiting_for || 1
  sessionId.value = data.session_id || ''
  
  // If session is ready, redirect
  if (data.session_ready || currentPlayers.value >= requiredPlayers.value) {
    stopPolling()
    router.push('/trading')
  }
}

const startPolling = () => {
  if (pollInterval.value) return
  
  pollInterval.value = setInterval(async () => {
    await checkStatus()
  }, 3000) // Poll every 3 seconds
}

const stopPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

// Lifecycle
onMounted(async () => {
  await joinWaitingRoom()
})

onUnmounted(() => {
  stopPolling()
})
</script> 