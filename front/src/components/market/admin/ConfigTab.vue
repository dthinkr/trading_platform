<template>
  <div class="config-tab">
    <!-- Market Configuration -->
    <v-card elevation="1" class="mb-4">
      <v-card-title class="compact-title">
        <v-icon left color="deep-blue" size="18">mdi-cog-outline</v-icon>
        Market Configuration
      </v-card-title>

      <v-card-text>
        <v-form>
          <div class="parameter-grid">
            <!-- Order Throttling Settings -->
            <v-card outlined class="parameter-card">
              <v-card-title class="compact-group-title">
                <v-icon left color="deep-blue" size="16">mdi-timer-settings-outline</v-icon>
                Order Throttling
              </v-card-title>
              <v-card-text class="pa-2">
                <v-row dense>
                  <template v-for="traderType in traderTypes" :key="traderType">
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="formState.throttle_settings[traderType].order_throttle_ms"
                        :label="`${formatTraderType(traderType)} (ms)`"
                        type="number"
                        min="0"
                        density="compact"
                        variant="outlined"
                        hide-details="auto"
                        class="mb-1 compact-input"
                        @input="updatePersistentSettings"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="formState.throttle_settings[traderType].max_orders_per_window"
                        :label="`${formatTraderType(traderType)} Max`"
                        type="number"
                        min="1"
                        density="compact"
                        variant="outlined"
                        hide-details="auto"
                        class="mb-1 compact-input"
                        @input="updatePersistentSettings"
                      ></v-text-field>
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
            >
              <v-card-title class="compact-group-title">
                <v-icon left color="deep-blue" size="16">mdi-label-outline</v-icon>
                {{ formatGroupTitle(hint) }}
              </v-card-title>
              <v-card-text class="pa-2">
                <v-row dense>
                  <v-col cols="6" v-for="field in group" :key="field.name">
                    <!-- Dropdown for agentic_prompt_template -->
                    <v-select
                      v-if="field.name === 'agentic_prompt_template'"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      :items="agenticTemplates"
                      item-title="name"
                      item-value="id"
                      density="compact"
                      variant="outlined"
                      hide-details="auto"
                      class="mb-1 compact-input"
                      :class="getFieldStyle(field.name)"
                      @update:modelValue="updatePersistentSettings"
                    ></v-select>
                    <!-- Boolean switch -->
                    <v-switch
                      v-else-if="field.type === 'boolean'"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      density="compact"
                      hide-details="auto"
                      color="primary"
                      class="mb-1 compact-input"
                      :class="getFieldStyle(field.name)"
                      @update:modelValue="updatePersistentSettings"
                    ></v-switch>
                    <!-- Array fields -->
                    <v-text-field
                      v-else-if="isArrayField(field)"
                      :label="field.title || ''"
                      v-model="formState[field.name]"
                      density="compact"
                      variant="outlined"
                      hide-details="auto"
                      class="mb-1 compact-input"
                      :class="getFieldStyle(field.name)"
                      @input="handleArrayInput(field.name, $event)"
                    ></v-text-field>
                    <!-- Regular fields -->
                    <v-text-field
                      v-else
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

    <!-- Treatment Sequence -->
    <v-card elevation="1" class="mb-4">
      <v-card-title class="compact-title" @click="showTreatments = !showTreatments" style="cursor: pointer">
        <v-icon left color="deep-blue" size="18">mdi-flask-outline</v-icon>
        Treatment Sequence
        <v-spacer></v-spacer>
        <v-icon>{{ showTreatments ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-card-title>

      <v-expand-transition>
        <div v-show="showTreatments">
          <v-card-text>
            <v-alert type="info" density="compact" class="mb-3">
              Define different trader compositions for each market.
            </v-alert>
            
            <v-textarea
              v-model="treatmentYaml"
              label="Treatment YAML"
              rows="10"
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
            <v-btn color="secondary" @click="loadTreatments" :disabled="!serverActive" size="small" variant="outlined">
              <v-icon start size="16">mdi-refresh</v-icon>
              Load
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn color="primary" @click="saveTreatments" :disabled="!serverActive" size="small" variant="elevated">
              <v-icon start size="16">mdi-content-save</v-icon>
              Save
            </v-btn>
          </v-card-actions>
        </div>
      </v-expand-transition>
    </v-card>

    <!-- Prolific Settings (Collapsed) -->
    <v-card elevation="1">
      <v-card-title class="compact-title" @click="showProlific = !showProlific" style="cursor: pointer">
        <v-icon left color="deep-blue" size="18">mdi-account-group-outline</v-icon>
        Prolific Settings
        <v-spacer></v-spacer>
        <v-icon>{{ showProlific ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-card-title>

      <v-expand-transition>
        <div v-show="showProlific">
          <v-card-text class="pa-3">
            <v-form>
              <v-textarea
                v-model="prolificSettings.credentials"
                label="Prolific Credentials"
                variant="outlined"
                density="compact"
                hide-details="auto"
                class="mb-2"
                placeholder="username1,password1&#10;username2,password2"
                hint="One username,password pair per line"
                persistent-hint
                rows="3"
              ></v-textarea>

              <div class="d-flex align-center mb-2">
                <v-text-field
                  v-model="numCredentials"
                  label="Count"
                  type="number"
                  min="1"
                  max="20"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="mr-2"
                  style="max-width: 100px"
                ></v-text-field>
                <v-btn color="secondary" @click="generateCredentials" :loading="generatingCredentials" size="small">
                  <v-icon start size="16">mdi-key-variant</v-icon>
                  Generate
                </v-btn>
              </div>

              <v-text-field
                v-model="prolificSettings.studyId"
                label="Study ID"
                variant="outlined"
                density="compact"
                hide-details="auto"
                class="mb-2"
              ></v-text-field>

              <v-text-field
                v-model="prolificSettings.redirectUrl"
                label="Redirect URL"
                variant="outlined"
                density="compact"
                hide-details="auto"
                class="mb-2"
              ></v-text-field>

              <v-btn color="primary" block @click="saveProlificSettings" :loading="savingProlific" size="small" variant="elevated">
                <v-icon start size="16">mdi-content-save</v-icon>
                Save Prolific Settings
              </v-btn>
            </v-form>
          </v-card-text>
        </div>
      </v-expand-transition>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from '@/api/axios'
import { debounce } from 'lodash'
import { useUIStore } from '@/store/ui'
import Haikunator from 'haikunator'

const props = defineProps({
  formState: { type: Object, required: true },
  formFields: { type: Array, required: true },
  serverActive: { type: Boolean, required: true },
})

const emit = defineEmits(['update:formState'])

const uiStore = useUIStore()
const haikunator = new Haikunator()

// Treatment state
const showTreatments = ref(false)
const treatmentYaml = ref('')
const treatments = ref([])
const yamlError = ref('')
const agenticTemplates = ref([])

// Prolific state
const showProlific = ref(false)
const prolificSettings = ref({ credentials: '', studyId: '', redirectUrl: '' })
const numCredentials = ref(5)
const generatingCredentials = ref(false)
const savingProlific = ref(false)

const traderTypes = ['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK', 'SIMPLE_ORDER']

const formatTraderType = (type) => {
  return type.replace('_', ' ').toLowerCase().split(' ').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ').substring(0, 10)
}

const formatGroupTitle = (hint) => {
  const titleMap = {
    'agentic_parameter': 'AI Agentic Traders',
    'model_parameter': 'Model Parameters',
    'noise_parameter': 'Noise Traders',
    'informed_parameter': 'Informed Traders',
    'human_parameter': 'Human Traders',
    'manipulator_parameter': 'Manipulator Traders',
  }
  return titleMap[hint] || hint.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const groupedFields = computed(() => {
  const groups = {}
  const filteredFields = props.formFields.filter(field => field.name !== 'throttle_settings')
  filteredFields.forEach((field) => {
    const hint = field.hint || 'other'
    if (!groups[hint]) groups[hint] = []
    groups[hint].push(field)
  })
  return groups
})

const getFieldType = (field) => {
  if (!field || !field.type) return 'text'
  return ['number', 'integer'].includes(field.type) ? 'number' : 'text'
}

const isArrayField = (field) => field.type === 'array'

const handleArrayInput = (fieldName, event) => {
  const value = typeof event === 'object' && event?.target ? event.target.value : String(event ?? '')
  if (fieldName === 'predefined_goals') {
    props.formState[fieldName] = value === '' ? [] : value.split(',').map((v) => parseInt(v.trim())).filter((n) => !isNaN(n))
  } else {
    props.formState[fieldName] = value === '' ? [] : value.split(',').map((item) => item.trim())
  }
  updatePersistentSettings()
}

const getFieldStyle = (fieldName) => {
  const defaultValue = props.formFields.find((f) => f.name === fieldName)?.default
  const currentValue = props.formState[fieldName]
  const isDifferent = (() => {
    if (Array.isArray(defaultValue) || Array.isArray(currentValue)) {
      return JSON.stringify(defaultValue) !== JSON.stringify(currentValue)
    }
    if (typeof defaultValue === 'number' || typeof currentValue === 'number') {
      return Number(defaultValue) !== Number(currentValue)
    }
    return defaultValue !== currentValue
  })()
  return isDifferent ? 'treatment-value' : ''
}

const debouncedUpdate = debounce(async (settings) => {
  try {
    const cleanSettings = { ...settings }
    if (cleanSettings.throttle_settings) {
      Object.entries(cleanSettings.throttle_settings).forEach(([trader, config]) => {
        cleanSettings.throttle_settings[trader] = {
          order_throttle_ms: parseInt(config.order_throttle_ms) || 0,
          max_orders_per_window: parseInt(config.max_orders_per_window) || 1,
        }
      })
    }
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_base_settings`, { settings: cleanSettings })
  } catch (error) {
    console.error('Failed to update settings:', error)
  }
}, 500)

const updatePersistentSettings = () => {
  emit('update:formState', props.formState)
  debouncedUpdate(props.formState)
}

const saveSettings = async () => {
  try {
    updatePersistentSettings()
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/reset_state`)
    uiStore.showSuccess('Settings saved')
  } catch (error) {
    console.error('Error saving settings:', error)
    uiStore.showError('Failed to save settings')
  }
}

// Treatment functions
const loadTreatments = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_treatments`)
    treatmentYaml.value = response.data.yaml_content || ''
    treatments.value = response.data.treatments || []
    yamlError.value = ''
  } catch (error) {
    yamlError.value = 'Failed to load treatments'
  }
}

const saveTreatments = async () => {
  try {
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_treatments`, { yaml_content: treatmentYaml.value })
    treatments.value = response.data.treatments || []
    yamlError.value = ''
    uiStore.showSuccess('Treatments saved')
  } catch (error) {
    yamlError.value = error.response?.data?.detail || 'Failed to save'
  }
}

const loadAgenticTemplates = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/agentic_templates`)
    agenticTemplates.value = response.data.templates || []
  } catch (error) {
    agenticTemplates.value = [{ id: 'buyer_20_default', name: 'Buyer (20 shares)' }]
  }
}

// Prolific functions
const fetchProlificSettings = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`)
    if (response.data?.data) {
      prolificSettings.value = {
        credentials: response.data.data.PROLIFIC_CREDENTIALS || '',
        studyId: response.data.data.PROLIFIC_STUDY_ID || '',
        redirectUrl: response.data.data.PROLIFIC_REDIRECT_URL || '',
      }
    }
  } catch (error) {
    console.error('Failed to fetch Prolific settings:', error)
  }
}

const saveProlificSettings = async () => {
  try {
    savingProlific.value = true
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`, {
      settings: {
        PROLIFIC_CREDENTIALS: prolificSettings.value.credentials,
        PROLIFIC_STUDY_ID: prolificSettings.value.studyId,
        PROLIFIC_REDIRECT_URL: prolificSettings.value.redirectUrl,
      },
    })
    uiStore.showSuccess('Prolific settings saved')
  } catch (error) {
    uiStore.showError('Failed to save Prolific settings')
  } finally {
    savingProlific.value = false
  }
}

const generateCredentials = () => {
  generatingCredentials.value = true
  try {
    const count = parseInt(numCredentials.value) || 5
    const generated = []
    for (let i = 0; i < count; i++) {
      const username = haikunator.haikunate({ tokenLength: 0, delimiter: '' })
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
      let password = ''
      for (let j = 0; j < 10; j++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length))
      }
      generated.push(`${username},${password}`)
    }
    prolificSettings.value.credentials = generated.join('\n')
    uiStore.showSuccess(`Generated ${count} credentials`)
  } finally {
    generatingCredentials.value = false
  }
}

onMounted(() => {
  if (props.serverActive) {
    loadTreatments()
    loadAgenticTemplates()
    fetchProlificSettings()
  }
})

watch(() => props.serverActive, (newVal) => {
  if (newVal) {
    loadTreatments()
    loadAgenticTemplates()
    fetchProlificSettings()
  }
})
</script>

<style scoped>
.config-tab {
  max-width: 1200px;
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

.compact-group-title {
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  padding: 0.3rem 0.5rem !important;
  background: rgba(248, 250, 252, 0.6);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  color: #374151 !important;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 0.5rem;
  align-items: start;
}

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 6px !important;
}

.compact-input {
  font-size: 0.85rem;
}

.treatment-value :deep(.v-field) {
  border: 1px solid #f44336 !important;
}

.treatment-value :deep(.v-label) {
  color: #f44336 !important;
}

.yaml-editor :deep(textarea) {
  font-family: 'Monaco', 'Menlo', monospace !important;
  font-size: 0.8rem !important;
}

.custom-btn {
  text-transform: none !important;
  font-weight: 500 !important;
}
</style>
