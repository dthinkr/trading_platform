<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-center space-x-2">
        <ClockIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
        <h2 class="text-base font-semibold text-neutral-900">Order Throttling</h2>
      </div>
    </div>
    
    <div class="card-body p-4">
      <div class="overflow-x-auto">
        <table class="min-w-full">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="text-left py-2 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                Trader Type
              </th>
              <th class="text-left py-2 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                Throttle (ms)
              </th>
              <th class="text-left py-2 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                Max Orders
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="traderType in traderTypes" :key="traderType" class="hover:bg-neutral-25">
              <td class="py-2 pr-4">
                <div class="flex items-center">
                  <UserIcon class="h-3 w-3 text-neutral-400 mr-2" aria-hidden="true" />
                  <div class="text-xs font-medium text-neutral-900">
                    {{ traderType }}
                  </div>
                </div>
              </td>
              <td class="py-2 pr-4">
                <input
                  v-model.number="throttleSettings[traderType].order_throttle_ms"
                type="number"
                min="0"
                  class="input w-20 text-xs py-1"
                @input="updateSettings"
                />
            </td>
              <td class="py-2">
                <input
                  v-model.number="throttleSettings[traderType].max_orders_per_window"
                type="number"
                min="1"
                  class="input w-16 text-xs py-1"
                @input="updateSettings"
                />
            </td>
          </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Compact help text -->
      <div class="mt-3 p-2 bg-blue-25 rounded text-xs text-blue-700">
        <div class="flex items-start">
          <InformationCircleIcon class="h-3 w-3 text-blue-500 mt-0.5 mr-1.5 flex-shrink-0" aria-hidden="true" />
          <div>
            <span class="font-medium">Throttle:</span> Min time between orders (ms) • 
            <span class="font-medium">Max Orders:</span> Per time window • 
            <span class="font-medium">HUMAN:</span> Settings for human traders
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, defineEmits } from 'vue'
import { 
  ClockIcon, 
  UserIcon, 
  InformationCircleIcon 
} from '@heroicons/vue/24/outline'

const props = defineProps({
  formState: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:formState'])

const traderTypes = ['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK', 'SIMPLE_ORDER']

const throttleSettings = computed({
  get: () => props.formState.throttle_settings || {
    HUMAN: { order_throttle_ms: 1000, max_orders_per_window: 2 },
    NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
    MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
    SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
  },
  set: (val) => {
    const newFormState = { ...props.formState, throttle_settings: val }
    emit('update:formState', newFormState)
  }
})

const updateSettings = () => {
  throttleSettings.value = { ...throttleSettings.value }
}
</script>

<style scoped>
.v-data-table :deep(td) {
  padding: 0 7px !important;
}

.v-data-table :deep(.v-data-table__wrapper > table > tbody > tr > td:last-child) {
  width: 1%;
  white-space: nowrap;
}
</style>
