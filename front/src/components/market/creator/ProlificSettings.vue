<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-center space-x-2">
        <UsersIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
        <h2 class="text-base font-semibold text-neutral-900">Prolific Settings</h2>
      </div>
    </div>
    
    <div class="card-body p-4 space-y-3">
      <!-- Study ID -->
      <div>
        <label class="block text-xs font-medium text-neutral-700 mb-1">Study ID</label>
        <input
          v-model="settings.studyId"
          type="text"
          class="input text-xs py-1"
          placeholder="Enter study ID"
        />
      </div>

      <!-- Redirect URL -->
      <div>
        <label class="block text-xs font-medium text-neutral-700 mb-1">Redirect URL</label>
        <input
          v-model="settings.redirectUrl"
          type="url"
          class="input text-xs py-1"
          placeholder="https://app.prolific.com/..."
        />
      </div>

      <!-- Credentials - Compact -->
      <div>
        <label class="block text-xs font-medium text-neutral-700 mb-1">Credentials</label>
        <div class="flex space-x-2">
          <input
            v-model.number="numCredentials"
            type="number"
            min="1"
            max="20"
            class="input text-xs py-1 w-16"
          />
          <button
            @click="generateCredentials"
            :disabled="generatingCredentials"
            class="btn btn-secondary text-xs px-2 py-1 flex-1 flex items-center justify-center"
          >
            <div v-if="generatingCredentials" class="spinner h-3 w-3 mr-1"></div>
            <KeyIcon v-else class="h-3 w-3 mr-1" aria-hidden="true" />
            Generate
          </button>
        </div>
        <textarea
          v-model="settings.credentials"
          rows="3"
          class="input text-xs py-1 mt-1 resize-none"
          placeholder="user1,pass1&#10;user2,pass2"
        ></textarea>
      </div>

      <!-- Error Message -->
      <div v-if="credentialsError" class="p-2 bg-red-50 border border-red-200 rounded text-xs">
        <div class="flex items-start">
          <ExclamationTriangleIcon class="h-3 w-3 text-red-400 mr-1 flex-shrink-0 mt-0.5" />
          <span class="text-red-800">{{ credentialsError }}</span>
        </div>
      </div>

      <!-- Save Button -->
      <button
        @click="saveSettings"
        :disabled="saving || !!credentialsError"
        class="btn btn-primary text-xs px-3 py-1.5 w-full flex items-center justify-center"
      >
        <div v-if="saving" class="spinner h-3 w-3 mr-1"></div>
        <CheckIcon v-else class="h-3 w-3 mr-1" aria-hidden="true" />
        Save Settings
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { 
  UsersIcon, 
  KeyIcon, 
  ExclamationTriangleIcon, 
  CheckIcon 
} from '@heroicons/vue/24/outline'
import axios from '@/api/axios'

const settings = ref({
  credentials: '',
  studyId: '',
  redirectUrl: ''
})
const saving = ref(false)
const numCredentials = ref(5)
const generatingCredentials = ref(false)

// Validate credentials format
const credentialsError = computed(() => {
  if (!settings.value.credentials.trim()) return null
  
  const lines = settings.value.credentials.trim().split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue // Skip empty lines
    
    const parts = line.split(',')
    if (parts.length !== 2) {
      return `Line ${i+1}: Must be username,password format`
    }
    
    const [username, password] = parts
    if (!username.trim() || !password.trim()) {
      return `Line ${i+1}: Username and password required`
    }
  }
  
  return null
})

// Fetch Prolific settings from the server
const fetchSettings = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`)
    if (response.data && response.data.data) {
      settings.value = {
        credentials: response.data.data.PROLIFIC_CREDENTIALS || '',
        studyId: response.data.data.PROLIFIC_STUDY_ID || '',
        redirectUrl: response.data.data.PROLIFIC_REDIRECT_URL || ''
      }
    }
  } catch (error) {
    console.error("Failed to fetch Prolific settings:", error)
  }
}

// Save Prolific settings to the server
const saveSettings = async () => {
  // Validate credentials before saving
  if (credentialsError.value) {
    console.error(credentialsError.value)
    return
  }
  
  try {
    saving.value = true
    
    const settingsData = {
      PROLIFIC_CREDENTIALS: settings.value.credentials,
      PROLIFIC_STUDY_ID: settings.value.studyId,
      PROLIFIC_REDIRECT_URL: settings.value.redirectUrl
    }
    
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`, { settings: settingsData })
    
    console.log('Prolific settings saved successfully')
  } catch (error) {
    console.error("Failed to save Prolific settings:", error)
  } finally {
    saving.value = false
  }
}

// Simple random string generator
const generateRandomString = (length = 8) => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// Generate random username and password pairs
const generateCredentials = () => {
  generatingCredentials.value = true
  
  try {
    const count = parseInt(numCredentials.value) || 5
    const generatedCredentials = []
    
    // Generate the specified number of credential pairs
    for (let i = 0; i < count; i++) {
      // Generate unique username and password
      const username = `user_${generateRandomString(6)}`
      const password = generateRandomString(12)
      
      generatedCredentials.push(`${username},${password}`)
    }
    
    // Set the generated credentials
    settings.value.credentials = generatedCredentials.join('\n')
  } catch (error) {
    console.error('Error generating credentials:', error)
  } finally {
    generatingCredentials.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.headline {
  font-size: 1.35rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.deep-blue {
  color: #1a237e !important;
}
</style>
