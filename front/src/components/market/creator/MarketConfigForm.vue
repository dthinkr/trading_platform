<template>
  <v-card elevation="2">
    <v-card-title class="headline">
      <v-icon left color="deep-blue">mdi-cog-outline</v-icon>
      Trading Market Configuration
    </v-card-title>

    <v-card-subtitle class="py-2">
      <v-chip small outlined color="error" class="mr-2">
        <v-icon left small color="error">mdi-information-outline</v-icon>
        Highlighted fields in red indicate treatment values that differ from defaults
      </v-chip>
    </v-card-subtitle>

    <v-card-text>
      <v-form>
        <div class="parameter-grid">
          <v-card
            v-for="(group, hint) in groupedFields"
            :key="hint"
            outlined
            class="parameter-card"
            :class="{ 'parameter-card-large': group.length > 4 }"
          >
            <v-card-title class="subtitle-1 py-2 px-3 grey lighten-4">
              <v-icon left color="deep-blue" small>mdi-label-outline</v-icon>
              {{ hint.replace('_', ' ') }}
            </v-card-title>
            <v-card-text class="pa-3">
              <v-row dense>
                <v-col cols="12" v-for="field in group" :key="field.name">
                  <v-text-field
                    v-if="!isArrayField(field)"
                    :label="field.title || ''"
                    v-model="formState[field.name]"
                    :type="getFieldType(field)"
                    dense
                    outlined
                    hide-details="auto"
                    class="mb-2 short-input"
                    :class="getFieldStyle(field.name)"
                    @input="updatePersistentSettings"
                  ></v-text-field>
                  <v-text-field
                    v-else
                    :label="field.title || ''"
                    v-model="formState[field.name]"
                    dense
                    outlined
                    hide-details="auto"
                    class="mb-2 short-input"
                    :class="getFieldStyle(field.name)"
                    @input="handleArrayInput(field.name, $event)"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </div>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        @click="saveSettings"
        :disabled="!serverActive"
        small
        elevation="2"
        class="custom-btn"
      >
        <v-icon left small>mdi-content-save</v-icon>
        Save Settings
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue'
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

const groupedFields = computed(() => {
  const groups = {}
  props.formFields.forEach((field) => {
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

const handleArrayInput = (fieldName, value) => {
  if (fieldName === 'predefined_goals') {
    if (value === '') {
      props.formState[fieldName] = []
    } else if (Array.isArray(value)) {
      props.formState[fieldName] = value.map((v) => parseInt(v))
    } else {
      // Convert string input to array of numbers
      props.formState[fieldName] = value
        .split(',')
        .map((v) => parseInt(v.trim()))
        .filter((n) => !isNaN(n))
    }
    console.log(`Updated ${fieldName}:`, props.formState[fieldName]) // Debug log
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

    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, {
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
.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  align-items: start;
}

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.parameter-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.parameter-card-large {
  grid-column: span 2;
}

.short-input {
  max-width: 100%;
  font-family: 'Inter', sans-serif;
}

.treatment-value {
  background-color: rgba(244, 67, 54, 0.05) !important; /* Light red background */
}

.treatment-value :deep(.v-input__slot) {
  border: 2px solid #f44336 !important; /* Red border */
}

.treatment-value :deep(.v-label) {
  color: #f44336 !important; /* Red label */
  font-weight: 600;
}

.treatment-value :deep(input) {
  color: #f44336 !important; /* Red text */
  font-weight: 600;
}
</style>
