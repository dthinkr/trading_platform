<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <CogIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
          <h2 class="text-base font-semibold text-neutral-900">Market Configuration</h2>
        </div>
        <div class="flex items-center space-x-3">
          <div class="flex items-center space-x-1.5 text-xs text-red-600">
            <ExclamationTriangleIcon class="h-3 w-3" aria-hidden="true" />
            <span>Red = Modified from defaults</span>
          </div>
          <button
            @click="toggleAllSections"
            class="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded border border-blue-200 hover:bg-blue-50"
          >
            {{ allExpanded ? 'Collapse All' : 'Expand All' }}
          </button>
        </div>
      </div>
    </div>
    
    <div class="card-body p-4">
      <!-- Expandable Sections -->
      <div class="space-y-4">
        
        <!-- Trader Configuration -->
        <div class="border border-neutral-200 rounded-lg">
          <button
            @click="toggleSection('traders')"
            class="w-full flex items-center justify-between p-3 hover:bg-neutral-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <UsersIcon class="h-4 w-4 text-blue-600" />
              <span class="text-sm font-medium text-neutral-900">Trader Configuration</span>
              <span class="text-xs text-neutral-500">({{ getFieldCount('traders') }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.traders ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.traders" class="p-3 border-t border-neutral-200 bg-neutral-25">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div v-for="field in traderFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

        <!-- Market Structure -->
        <div class="border border-neutral-200 rounded-lg">
          <button
            @click="toggleSection('market')"
            class="w-full flex items-center justify-between p-3 hover:bg-neutral-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <ChartBarIcon class="h-4 w-4 text-green-600" />
              <span class="text-sm font-medium text-neutral-900">Market Structure</span>
              <span class="text-xs text-neutral-500">({{ getFieldCount('market') }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.market ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.market" class="p-3 border-t border-neutral-200 bg-neutral-25">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div v-for="field in marketStructureFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

        <!-- Trading Behavior -->
        <div class="border border-neutral-200 rounded-lg">
          <button
            @click="toggleSection('behavior')"
            class="w-full flex items-center justify-between p-3 hover:bg-neutral-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <CursorArrowRaysIcon class="h-4 w-4 text-purple-600" />
              <span class="text-sm font-medium text-neutral-900">Trading Behavior</span>
              <span class="text-xs text-neutral-500">({{ getFieldCount('behavior') }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.behavior ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.behavior" class="p-3 border-t border-neutral-200 bg-neutral-25">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div v-for="field in behaviorFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

        <!-- Informed Trader Settings -->
        <div class="border border-neutral-200 rounded-lg">
          <button
            @click="toggleSection('informed')"
            class="w-full flex items-center justify-between p-3 hover:bg-neutral-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <EyeIcon class="h-4 w-4 text-orange-600" />
              <span class="text-sm font-medium text-neutral-900">Informed Trader Settings</span>
              <span class="text-xs text-neutral-500">({{ getFieldCount('informed') }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.informed ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.informed" class="p-3 border-t border-neutral-200 bg-neutral-25">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div v-for="field in informedFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

        <!-- System & Admin -->
        <div class="border border-neutral-200 rounded-lg">
          <button
            @click="toggleSection('system')"
            class="w-full flex items-center justify-between p-3 hover:bg-neutral-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <CogIcon class="h-4 w-4 text-red-600" />
              <span class="text-sm font-medium text-neutral-900">System & Admin</span>
              <span class="text-xs text-neutral-500">({{ getFieldCount('system') }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.system ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.system" class="p-3 border-t border-neutral-200 bg-neutral-25">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div v-for="field in systemFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

        <!-- Any uncategorized fields -->
        <div v-if="uncategorizedFields.length > 0" class="border border-yellow-200 rounded-lg">
          <button
            @click="toggleSection('other')"
            class="w-full flex items-center justify-between p-3 hover:bg-yellow-25 rounded-t-lg"
          >
            <div class="flex items-center space-x-2">
              <QuestionMarkCircleIcon class="h-4 w-4 text-yellow-600" />
              <span class="text-sm font-medium text-neutral-900">Other Settings</span>
              <span class="text-xs text-neutral-500">({{ uncategorizedFields.length }} fields)</span>
            </div>
            <ChevronDownIcon :class="['h-4 w-4 text-neutral-400 transition-transform', expandedSections.other ? 'rotate-180' : '']" />
          </button>
          <div v-show="expandedSections.other" class="p-3 border-t border-yellow-200 bg-yellow-25">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div v-for="field in uncategorizedFields" :key="field.name" class="space-y-1">
                <label class="block text-xs font-medium text-neutral-700">{{ field.title }}</label>
                <FieldInput :field="field" :value="formState[field.name]" @update="updateField" />
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue'
import { 
  CogIcon, 
  ExclamationTriangleIcon,
  ChevronDownIcon,
  UsersIcon,
  ChartBarIcon,
  CursorArrowRaysIcon,
  EyeIcon,
  QuestionMarkCircleIcon
} from '@heroicons/vue/24/outline'
import axios from '@/api/axios'
import FieldInput from './FieldInput.vue'

const props = defineProps({
  formState: {
    type: Object,
    required: true
  },
  formFields: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:formState'])

// Expandable sections state
const expandedSections = ref({
  traders: true,
  market: false,
  behavior: false,
  informed: false,
  system: false,
  other: false
})

const allExpanded = computed(() => {
  return Object.values(expandedSections.value).every(val => val)
})

// Field categorization - comprehensive lists
const traderFields = computed(() => {
  return props.formFields.filter(field => 
    ['num_noise_traders', 'num_informed_traders', 'num_simple_order_traders', 
     'trading_day_duration', 'activity_frequency', 'execution_throttle_ms'].includes(field.name)
  )
})

const marketStructureFields = computed(() => {
  return props.formFields.filter(field => 
    ['orders_per_level_at_book_start', 'depth_book_shown', 'order_book_levels', 
     'default_price', 'lira_gbp_conversion_rate', 'initial_cash', 'initial_stocks'].includes(field.name)
  )
})

const behaviorFields = computed(() => {
  return props.formFields.filter(field => 
    ['step', 'order_amount', 'passive_order_prob', 'cancel_order_prob', 'bid_order_prob',
     'use_passive_orders', 'randomly_flip_trade_direction', 'share_passive_orders',
     'trade_intensity', 'trade_direction'].includes(field.name)
  )
})

const informedFields = computed(() => {
  return props.formFields.filter(field => 
    ['informed_edge', 'informed_order_book_levels', 'informed_order_book_depth'].includes(field.name)
  )
})

const systemFields = computed(() => {
  return props.formFields.filter(field => 
    ['cancel_time', 'max_markets_per_human', 'google_form_id', 'admin_users',
     'predefined_goals', 'allow_random_goals'].includes(field.name)
  )
})

// Any fields that don't fit into the above categories
const uncategorizedFields = computed(() => {
  const categorizedFieldNames = new Set([
    ...traderFields.value.map(f => f.name),
    ...marketStructureFields.value.map(f => f.name),
    ...behaviorFields.value.map(f => f.name),
    ...informedFields.value.map(f => f.name),
    ...systemFields.value.map(f => f.name)
  ])
  
  return props.formFields.filter(field => !categorizedFieldNames.has(field.name))
})

// Helper functions
const toggleSection = (section) => {
  expandedSections.value[section] = !expandedSections.value[section]
}

const toggleAllSections = () => {
  const shouldExpand = !allExpanded.value
  Object.keys(expandedSections.value).forEach(key => {
    expandedSections.value[key] = shouldExpand
  })
}

const getFieldCount = (section) => {
  const fieldMaps = {
    traders: traderFields,
    market: marketStructureFields,
    behavior: behaviorFields,
    informed: informedFields,
    system: systemFields
  }
  return fieldMaps[section]?.value?.length || 0
}

const updateField = (fieldName, value) => {
  const newFormState = { ...props.formState }
  newFormState[fieldName] = value
  emit('update:formState', newFormState)
  updatePersistentSettings()
}

// Debounced update function
let updateTimeout = null
const debounce = (func, delay) => {
  return (...args) => {
    clearTimeout(updateTimeout)
    updateTimeout = setTimeout(() => func.apply(this, args), delay)
  }
}

const debouncedUpdate = debounce(async (settings) => {
  try {
    const cleanSettings = { ...settings }
    
    if (cleanSettings.throttle_settings) {
      Object.entries(cleanSettings.throttle_settings).forEach(([trader, config]) => {
        cleanSettings.throttle_settings[trader] = {
          order_throttle_ms: parseInt(config.order_throttle_ms) || 0,
          max_orders_per_window: parseInt(config.max_orders_per_window) || 1
        }
      })
    }
    
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, {
      settings: cleanSettings
    })
  } catch (error) {
    console.error("Failed to update persistent settings:", error)
    throw error
  }
}, 500)

const updatePersistentSettings = () => {
  debouncedUpdate(props.formState)
}


</script>
