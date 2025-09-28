<template>
  <v-card elevation="1">
    <v-card-title class="compact-title">
      <v-icon left color="deep-blue" size="18">mdi-account-group-outline</v-icon>
      Prolific Settings
    </v-card-title>
    <v-card-text class="pa-3">
      <v-form>
        <v-textarea
          v-model="settings.credentials"
          label="Prolific Credentials"
          variant="outlined"
          density="compact"
          hide-details="auto"
          class="mb-2"
          placeholder="username1,password1
username2,password2
username3,password3"
          hint="Enter one username,password pair per line. No commas in passwords."
          persistent-hint
          rows="3"
        ></v-textarea>

        <div class="d-flex align-center mb-2">
          <v-text-field
            v-model="numCredentials"
            label="Number of Credentials"
            type="number"
            min="1"
            max="20"
            variant="outlined"
            density="compact"
            hide-details
            class="mr-2"
            style="max-width: 140px"
          ></v-text-field>

          <v-btn
            color="secondary"
            @click="generateCredentials"
            :disabled="generatingCredentials"
            :loading="generatingCredentials"
            size="small"
          >
            <v-icon start size="16">mdi-key-variant</v-icon>
            Generate
          </v-btn>
        </div>

        <v-alert v-if="credentialsError" type="error" density="compact" class="mb-2">
          {{ credentialsError }}
        </v-alert>

        <v-text-field
          v-model="settings.studyId"
          label="Prolific Study ID"
          variant="outlined"
          density="compact"
          hide-details="auto"
          class="mb-2"
        ></v-text-field>

        <v-text-field
          v-model="settings.redirectUrl"
          label="Prolific Redirect URL"
          variant="outlined"
          density="compact"
          hide-details="auto"
          class="mb-2"
        ></v-text-field>

        <v-btn
          color="primary"
          block
          @click="saveSettings"
          class="mt-2"
          :loading="saving"
          :disabled="!!credentialsError"
          size="small"
          variant="elevated"
        >
          <v-icon start size="16">mdi-content-save</v-icon>
          Save Settings
        </v-btn>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from '@/api/axios'
import { useTraderStore } from '@/store/app'
import Haikunator from 'haikunator'

const traderStore = useTraderStore()
const haikunator = new Haikunator()

const settings = ref({
  credentials: '',
  studyId: '',
  redirectUrl: '',
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
      return `Line ${i + 1}: Each line must contain exactly one username and one password separated by a comma`
    }

    const [username, password] = parts
    if (!username.trim() || !password.trim()) {
      return `Line ${i + 1}: Username and password cannot be empty`
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
        redirectUrl: response.data.data.PROLIFIC_REDIRECT_URL || '',
      }
    }
  } catch (error) {
    console.error('Failed to fetch Prolific settings:', error)
  }
}

// Save Prolific settings to the server
const saveSettings = async () => {
  // Validate credentials before saving
  if (credentialsError.value) {
    traderStore.showSnackbar({
      text: credentialsError.value,
      color: 'error',
    })
    return
  }

  try {
    saving.value = true

    const settingsData = {
      PROLIFIC_CREDENTIALS: settings.value.credentials,
      PROLIFIC_STUDY_ID: settings.value.studyId,
      PROLIFIC_REDIRECT_URL: settings.value.redirectUrl,
    }

    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`, {
      settings: settingsData,
    })

    // Show success message
    traderStore.showSnackbar({
      text: 'Prolific settings saved successfully',
      color: 'success',
    })
  } catch (error) {
    console.error('Failed to save Prolific settings:', error)

    // Show error message
    traderStore.showSnackbar({
      text: 'Failed to save Prolific settings',
      color: 'error',
    })
  } finally {
    saving.value = false
  }
}

// Generate random username and password pairs
const generateCredentials = () => {
  generatingCredentials.value = true

  try {
    const count = parseInt(numCredentials.value) || 5
    const generatedCredentials = []

    // Generate the specified number of credential pairs
    for (let i = 0; i < count; i++) {
      // Generate a unique username using haikunator
      const username = haikunator.haikunate({ tokenLength: 0, delimiter: '' })

      // Generate a random password (8-12 characters, alphanumeric)
      const passwordLength = Math.floor(Math.random() * 5) + 8 // 8-12 characters
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
      let password = ''

      for (let j = 0; j < passwordLength; j++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length))
      }

      generatedCredentials.push(`${username},${password}`)
    }

    // Update the credentials field
    settings.value.credentials = generatedCredentials.join('\n')

    // Show success message
    traderStore.showSnackbar({
      text: `Generated ${count} credential pairs`,
      color: 'success',
    })
  } catch (error) {
    console.error('Error generating credentials:', error)

    traderStore.showSnackbar({
      text: 'Failed to generate credentials',
      color: 'error',
    })
  } finally {
    generatingCredentials.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.compact-title {
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.75rem !important;
  background: rgba(248, 250, 252, 0.8);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  color: #1e293b !important;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  gap: 0.75rem;
  text-align: center;
}

.loading-text {
  color: #666;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.success-message {
  color: #4caf50;
  font-weight: 500;
  margin-top: 0.75rem;
  text-align: center;
  font-size: 0.9rem;
}

.error-message {
  color: #f44336;
  font-weight: 500;
  margin-top: 0.75rem;
  text-align: center;
  font-size: 0.9rem;
}

.deep-blue {
  color: #1a237e !important;
}
</style>
