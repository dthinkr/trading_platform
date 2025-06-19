<template>
  <div class="space-y-6">
    <!-- Ready header -->
    <div class="text-center">
      <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <RocketLaunchIcon class="h-8 w-8 text-green-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Ready to Trade
      </h3>
      <p class="text-lg text-neutral-600">
        You are now ready to start your trading session
      </p>
    </div>

    <!-- Market Details -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Duration -->
      <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <div class="flex items-center mb-3">
          <ClockIcon class="h-6 w-6 text-blue-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-blue-900">Duration</h4>
        </div>
        <div class="space-y-3 text-blue-800">
          <p class="text-sm">
            Trade for <span class="font-semibold text-lg">15 minutes</span>
          </p>
        </div>
      </div>

      <!-- Market Progress -->
      <div class="bg-green-50 rounded-lg p-6 border border-green-200">
        <div class="flex items-center mb-3">
          <ChartBarIcon class="h-6 w-6 text-green-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-green-900">Market Progress</h4>
        </div>
        <div class="space-y-2 text-green-800 text-sm">
          <div class="flex justify-between">
            <span>Markets You Have Played:</span>
            <span class="font-semibold">0</span>
          </div>
          <div class="flex justify-between">
            <span>Markets You Can Still Play:</span>
            <span class="font-semibold">Multiple</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Trading Parameters -->
    <div class="border border-neutral-200 rounded-lg overflow-hidden">
      <div class="bg-neutral-50 px-4 py-3 border-b border-neutral-200">
        <h4 class="font-semibold text-neutral-900 flex items-center">
          <TableCellsIcon class="h-5 w-5 mr-2" aria-hidden="true" />
          Trading Parameters
        </h4>
      </div>
      <div class="p-4">
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-4 text-sm border-b border-neutral-100 pb-2">
            <div class="font-medium text-neutral-900">Parameter</div>
            <div class="font-medium text-neutral-900">Value</div>
          </div>
          
          <div class="grid grid-cols-2 gap-4 text-sm py-2">
            <div class="text-neutral-700">Goal</div>
            <div class="text-neutral-900">You will be assigned a specific trading goal at the start of each market</div>
          </div>
          
          <div class="grid grid-cols-2 gap-4 text-sm py-2 border-t border-neutral-100">
            <div class="text-neutral-700">Initial Shares</div>
            <div class="text-neutral-900">Will be set based on your assigned role</div>
          </div>
          
          <div class="grid grid-cols-2 gap-4 text-sm py-2 border-t border-neutral-100">
            <div class="text-neutral-700">Initial Cash</div>
            <div class="text-neutral-900">Will be provided in Liras for trading</div>
          </div>
          
          <div class="grid grid-cols-2 gap-4 text-sm py-2 border-t border-neutral-100">
            <div class="text-neutral-700">Currency</div>
            <div class="text-neutral-900">Liras</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Trading Objectives Info -->
    <div class="bg-yellow-50 rounded-lg p-6 border border-yellow-200">
      <h4 class="font-semibold text-yellow-900 mb-3 flex items-center">
        <ExclamationTriangleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        General Trading Objectives
      </h4>
      <div class="space-y-3 text-yellow-800">
        <p class="text-sm">
          At the beginning of each market you will be given a specific role. Potential tasks for your role could include:
        </p>
        <ul class="space-y-2 text-sm list-disc list-inside ml-4">
          <li>Buy a certain number of shares at the lowest price (Informed Trader)</li>
          <li>Sell a certain number of shares at the highest price (Informed Trader)</li>
          <li>Buy and Sell shares to generate profit (Speculator)</li>
        </ul>
        <div class="mt-4 p-3 bg-red-100 border border-red-200 rounded text-red-800 text-xs">
          <strong>Important Notice:</strong><br>
          If you don't complete your trading objective within the time limit, the platform will automatically complete the trades for you, which may affect your profits.
        </div>
      </div>
    </div>

    <!-- Market Participants Info -->
    <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
      <h4 class="font-semibold text-blue-900 mb-3 flex items-center">
        <UserGroupIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Market Participants
      </h4>
      <div class="space-y-3 text-blue-800">
        <p class="text-sm">
          The other participants in the market are all artificial (algorithmic) traders, i.e., non-human.
        </p>
        <div class="bg-blue-100 border border-blue-200 rounded p-3 text-xs">
          All artificial traders have no objective in terms of earnings. However, they may have tasks such as buying or selling a specific number of shares. For example, their trading activity can significantly shift the price either upward or downward.
        </div>
      </div>
    </div>

    <!-- Next Steps -->
    <div class="border border-neutral-200 rounded-lg p-6">
      <h4 class="font-semibold text-neutral-900 mb-4 flex items-center">
        <AcademicCapIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        What Happens Next
      </h4>
      <div class="space-y-3">
        <div class="flex items-start space-x-3">
          <div class="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
            <span class="text-xs font-medium text-green-600">1</span>
          </div>
          <div>
            <div class="font-medium text-neutral-900">Market Assignment</div>
            <div class="text-sm text-neutral-600">You will be assigned to a market with artificial traders</div>
          </div>
        </div>
        
        <div class="flex items-start space-x-3">
          <div class="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
            <span class="text-xs font-medium text-blue-600">2</span>
          </div>
          <div>
            <div class="font-medium text-neutral-900">Role Assignment</div>
            <div class="text-sm text-neutral-600">You will receive your specific trading goal and initial resources</div>
          </div>
        </div>
        
        <div class="flex items-start space-x-3">
          <div class="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
            <span class="text-xs font-medium text-purple-600">3</span>
          </div>
          <div>
            <div class="font-medium text-neutral-900">Start Trading</div>
            <div class="text-sm text-neutral-600">Begin trading for 15 minutes to achieve your goal</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirmation -->
    <div class="flex items-center justify-center">
      <label class="flex items-center space-x-3 cursor-pointer">
        <input
          type="checkbox"
          v-model="ready"
          @change="$emit('update:ready', ready)"
          class="h-4 w-4 text-green-600 focus:ring-green-500 border-neutral-300 rounded"
        />
        <span class="text-sm text-neutral-700">
          I understand the trading objectives and am ready to proceed to the markets
        </span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  RocketLaunchIcon,
  ClockIcon,
  ChartBarIcon,
  TableCellsIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  AcademicCapIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  ready: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:ready'])

// Local state
const ready = ref(props.ready)
</script> 