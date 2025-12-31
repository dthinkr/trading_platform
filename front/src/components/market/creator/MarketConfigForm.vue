<template>
  <v-card elevation="1">
    <v-card-title class="compact-title">
      <v-icon left color="deep-blue" size="18">mdi-cog-outline</v-icon>
      Trading Market Configuration
    </v-card-title>

    <v-card-text>
      <v-form>
        <div class="parameter-grid">
          <!-- Order Throttling Settings -->
          <v-card outlined class="parameter-card">
            <v-card-title class="compact-group-title">
              <v-icon left color="deep-blue" size="16">mdi-timer-settings-outline</v-icon>
              Order Throttling Settings
            </v-card-title>
            <v-card-text class="pa-2">
              <v-row dense>
                <template v-for="traderType in traderTypes" :key="traderType">
                  <v-col cols="6">
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props: tooltipProps }">
                        <v-text-field
                          v-bind="tooltipProps"
                          v-model.number="formState.throttle_settings[traderType].order_throttle_ms"
                          :label="`${formatTraderType(traderType)} Throttle (ms)`"
                          type="number"
                          min="0"
                          density="compact"
                          variant="outlined"
                          hide-details="auto"
                          class="mb-1 compact-input"
                          @input="updatePersistentSettings"
                        ></v-text-field>
                      </template>
                      <span class="tooltip-code">throttle_settings.{{ traderType }}.order_throttle_ms</span>
                    </v-tooltip>
                  </v-col>
                  <v-col cols="6">
                    <v-tooltip location="top">
                      <template v-slot:activator="{ props: tooltipProps }">
                        <v-text-field
                          v-bind="tooltipProps"
                          v-model.number="formState.throttle_settings[traderType].max_orders_per_window"
                          :label="`${formatTraderType(traderType)} Max Orders`"
                          type="number"
                          min="1"
                          density="compact"
                          variant="outlined"
                          hide-details="auto"
                          class="mb-1 compact-input"
                          @input="updatePersistentSettings"
                        ></v-text-field>
                      </template>
                      <span class="tooltip-code">throttle_settings.{{ traderType }}.max_orders_per_window</span>
                    </v-tooltip>
                  </v-col>
                </template>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Regular Parameter Groups -->
          <v-card
            v-for="(group, hint) in groupedFields"
            :key="hint"
            outlined
            class="parameter-card"
            :class="{ 'parameter-card-large': group.length > 4 }"
          >
            <v-card-title class="compact-group-title">
              <v-icon left color="deep-blue" size="16">mdi-label-outline</v-icon>
              {{ hint.replace('_', ' ') }}
            </v-card-title>
            <v-card-text class="pa-2">
              <v-row dense>
                <v-col cols="6" v-for="field in group" :key="field.name">
                  <v-tooltip location="top">
                    <template v-slot:activator="{ props: tooltipProps }">
                      <v-text-field
                        v-if="!isArrayField(field)"
                        v-bind="tooltipProps"
                        :label="field.title || ''"
                        v-model="formState[field.name]"
                        :type="getFieldType(field)"
                        density="compact"
                        variant="outlined"
                        hide-details="auto"
                        class="mb-1 compact-input"
                        :class="getFieldStyle(field.name)"
                        @input="updatePersistentSettings"
                      ></v-text-field>
                      <v-text-field
                        v-else
                        v-bind="tooltipProps"
                        :label="field.title || ''"
                        v-model="formState[field.name]"
                        density="compact"
                        variant="outlined"
                        hide-details="auto"
                        class="mb-1 compact-input"
                        :class="getFieldStyle(field.name)"
                        @input="handleArrayInput(field.name, $event)"
                      ></v-text-field>
                    </template>
                    <span class="tooltip-code">{{ field.name }}</span>
                  </v-tooltip>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </div>
      </v-form>
    </v-card-text>

    <v-card-actions class="pa-2">
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        @click="saveSettings"
        :disabled="!serverActive"
        size="small"
        variant="elevated"
        class="custom-btn"
      >
        <v-icon start size="16">mdi-content-save</v-icon>
        Save Settings
      </v-btn>
    </v-card-actions>
  </v-card>

  <v-card elevation="1" class="mt-4">
    <v-card-title class="compact-title" @click="showTreatments = !showTreatments" style="cursor: pointer">
      <v-icon left color="deep-blue" size="18">mdi-flask-outline</v-icon>
      Treatment Sequence (Per-Market Config)
      <v-spacer></v-spacer>
      <v-icon>{{ showTreatments ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
    </v-card-title>

    <v-expand-transition>
      <div v-show="showTreatments">
        <v-card-text>
          <v-alert type="info" density="compact" class="mb-3">
            Define different trader compositions for each market. Market 1 uses treatment 0, Market 2 uses treatment 1, etc.
          </v-alert>
          
          <v-textarea
            v-model="treatmentYaml"
            label="Treatment YAML"
            placeholder="treatments:
  - name: 'Market 1 - Noise Only'
    num_noise_traders: 5
    num_spoofing_traders: 0
  - name: 'Market 2 - With Spoofer'
    num_noise_traders: 3
    num_spoofing_traders: 1"
            rows="12"
            variant="outlined"
            density="compact"
            class="yaml-editor"
            :error="yamlError !== ''"
            :error-messages="yamlError"
          ></v-textarea>

          <div v-if="treatments.length > 0" class="mt-2">
            <v-chip
              v-for="(t, i) in treatments"
              :key="i"
              size="small"
              class="mr-1 mb-1"
              color="primary"
              variant="outlined"
            >
              {{ i }}: {{ t.name || `Treatment ${i}` }}
            </v-chip>
          </div>
        </v-card-text>

        <v-card-actions class="pa-2">
          <v-btn
            color="secondary"
            @click="loadTreatments"
            :disabled="!serverActive"
            size="small"
            variant="outlined"
            class="custom-btn"
          >
            <v-icon start size="16">mdi-refresh</v-icon>
            Load
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            @click="saveTreatments"
            :disabled="!serverActive"
            size="small"
            variant="elevated"
            class="custom-btn"
          >
            <v-icon start size="16">mdi-content-save</v-icon>
            Save Treatments
          </v-btn>
        </v-card-actions>
      </div>
    </v-expand-transition>
  </v-card>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits, onMounted, watch } from 'vue'
import axios from '@/api/axios'
import { debounce } from 'lodash'

const props = defineProps({
  formState: {
    type: Object,
    required: true,
  },
  formFields: {
    type: Array,
    required: true,
  },
  serverActive: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['update:formState'])

const showTreatments = ref(false)
const treatmentYaml = ref('')
const treatments = ref([])
const yamlError = ref('')

const loadTreatments = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_treatments`)
    treatmentYaml.value = response.data.yaml_content || ''
    treatments.value = response.data.treatments || []
    yamlError.value = ''
  } catch (error) {
    console.error('Failed to load treatments:', error)
    yamlError.value = 'Failed to load treatments'
  }
}

const saveTreatments = async () => {
  try {
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_treatments`, {
      yaml_content: treatmentYaml.value
    })
    treatments.value = response.data.treatments || []
    yamlError.value = ''
  } catch (error) {
    console.error('Failed to save treatments:', error)
    yamlError.value = error.response?.data?.detail || 'Failed to save treatments'
  }
}

onMounted(() => {
  if (props.serverActive) {
    loadTreatments()
  }
})

watch(() => props.serverActive, (newVal) => {
  if (newVal && treatments.value.length === 0) {
    loadTreatments()
  }
})

watch(showTreatments, (newVal) => {
  if (newVal && props.serverActive && treatments.value.length === 0) {
    loadTreatments()
  }
})

// Define trader types for throttling settings
const traderTypes = ['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK', 'SIMPLE_ORDER']

// Format trader type names for display
const formatTraderType = (type) => {
  return type.replace('_', ' ').toLowerCase().split(' ').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ').substring(0, 12)
}

const groupedFields = computed(() => {
  const groups = {}
  // Filter out throttle_settings since we handle it separately
  const filteredFields = props.formFields.filter(field => field.name !== 'throttle_settings')
  filteredFields.forEach((field) => {
    const hint = field.hint || 'other'
    if (!groups[hint]) {
      groups[hint] = []
    }
    groups[hint].push(field)
  })
  return groups
})

const getFieldType = (field) => {
  if (!field || !field.type) return 'text'
  return ['number', 'integer'].includes(field.type) ? 'number' : 'text'
}

const isArrayField = (field) => {
  return field.type === 'array'
}

const handleArrayInput = (fieldName, event) => {
  // Extract string value from event or use directly if already a string
  const value = typeof event === 'object' && event?.target ? event.target.value : String(event ?? '')
  
  if (fieldName === 'predefined_goals') {
    if (value === '') {
      props.formState[fieldName] = []
    } else {
      // Convert string input to array of numbers
      props.formState[fieldName] = value
        .split(',')
        .map((v) => parseInt(v.trim()))
        .filter((n) => !isNaN(n))
    }
    console.log(`Updated ${fieldName}:`, props.formState[fieldName])
  } else {
    // Handle other array fields
    props.formState[fieldName] = value === '' ? [] : value.split(',').map((item) => item.trim())
  }
  updatePersistentSettings()
}

const debouncedUpdate = debounce(async (settings) => {
  try {
    // Create a clean copy of the settings
    const cleanSettings = { ...settings }

    // Ensure throttle settings are properly formatted
    if (cleanSettings.throttle_settings) {
      Object.entries(cleanSettings.throttle_settings).forEach(([trader, config]) => {
        cleanSettings.throttle_settings[trader] = {
          order_throttle_ms: parseInt(config.order_throttle_ms) || 0,
          max_orders_per_window: parseInt(config.max_orders_per_window) || 1,
        }
      })
    }

    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_base_settings`, {
      settings: cleanSettings,
    })
  } catch (error) {
    console.error('Failed to update persistent settings:', error)
    throw error
  }
}, 500)

const updatePersistentSettings = () => {
  emit('update:formState', props.formState)
  debouncedUpdate(props.formState)
}

const saveSettings = async () => {
  try {
    await updatePersistentSettings()

    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/reset_state`)

    console.log('Settings saved and state reset successfully')
  } catch (error) {
    console.error('Error saving settings:', error)
  }
}

const getFieldStyle = (fieldName) => {
  const defaultValue = props.formFields.find((f) => f.name === fieldName)?.default
  const currentValue = props.formState[fieldName]

  // Check if the values are different, handling different types
  const isDifferent = (() => {
    // Handle array type fields
    if (Array.isArray(defaultValue) || Array.isArray(currentValue)) {
      return JSON.stringify(defaultValue) !== JSON.stringify(currentValue)
    }
    // Handle number type fields
    if (typeof defaultValue === 'number' || typeof currentValue === 'number') {
      return Number(defaultValue) !== Number(currentValue)
    }
    // Handle other types
    return defaultValue !== currentValue
  })()

  return isDifferent ? 'treatment-value' : ''
}
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

.compact-group-title {
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  padding: 0.3rem 0.5rem !important;
  background: rgba(248, 250, 252, 0.6);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  backdrop-filter: blur(4px);
  color: #374151 !important;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 0.5rem;
  align-items: start;
  margin-top: 0.5rem;
}

/* Removed custom throttling styles - now uses standard parameter card styling */

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
  border-radius: 6px !important;
}

.parameter-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.parameter-card-large {
  /* No span in single column layout */
}

.compact-input {
  max-width: 100%;
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
}

.treatment-value {
  background-color: rgba(244, 67, 54, 0.05) !important;
}

.treatment-value :deep(.v-field) {
  border: 1px solid #f44336 !important;
}

.treatment-value :deep(.v-label) {
  color: #f44336 !important;
  font-weight: 500;
}

.treatment-value :deep(input) {
  color: #f44336 !important;
  font-weight: 500;
}

/* Removed data table styles since we're using form fields now */

.custom-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: 0.5px !important;
  font-family: 'Inter', sans-serif !important;
}

.yaml-editor :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
  font-size: 0.8rem !important;
  line-height: 1.4 !important;
}

.tooltip-code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
}

@media (max-width: 960px) {
  .parameter-grid {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .parameter-card-large {
    grid-column: span 1;
  }
  
  .throttling-card {
    grid-column: 1;
  }
}
</style>
