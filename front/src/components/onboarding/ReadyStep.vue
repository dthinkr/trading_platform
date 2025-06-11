<template>
  <div class="space-y-6">
    <!-- Ready header -->
    <div class="text-center">
      <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <RocketLaunchIcon class="h-8 w-8 text-green-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Ready to Trade!
      </h3>
      <p class="text-lg text-neutral-600">
        You're all set to enter the live trading session
      </p>
    </div>

    <!-- Completion summary -->
    <div class="bg-green-50 rounded-lg p-6 border border-green-200">
      <h4 class="font-semibold text-green-900 mb-4 flex items-center">
        <CheckCircleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Onboarding Complete
      </h4>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="space-y-3">
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Terms and conditions accepted</span>
          </div>
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Trading instructions reviewed</span>
          </div>
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Practice session completed</span>
          </div>
        </div>
        <div class="space-y-3">
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Knowledge quiz passed</span>
          </div>
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Platform familiarization complete</span>
          </div>
          <div class="flex items-center text-green-700">
            <CheckCircleIcon class="h-4 w-4 mr-2" />
            <span class="text-sm">Ready for live trading</span>
          </div>
        </div>
      </div>
    </div>

    <!-- What to expect -->
    <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
      <h4 class="font-semibold text-blue-900 mb-3 flex items-center">
        <InformationCircleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        What to Expect Next
      </h4>
      <div class="space-y-3 text-blue-800">
        <div class="flex items-start space-x-3">
          <ClockIcon class="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-medium text-sm">Trading Session</p>
            <p class="text-sm">The live trading session will begin once you proceed. You'll have a set amount of time to trade.</p>
          </div>
        </div>
        <div class="flex items-start space-x-3">
          <UsersIcon class="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-medium text-sm">Other Traders</p>
            <p class="text-sm">You'll be trading alongside other participants in real-time.</p>
          </div>
        </div>
        <div class="flex items-start space-x-3">
          <ChartBarIcon class="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-medium text-sm">Real-Time Updates</p>
            <p class="text-sm">Order book, prices, and your portfolio will update in real-time.</p>
          </div>
        </div>
        <div class="flex items-start space-x-3">
          <TrophyIcon class="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <p class="font-medium text-sm">Your Goal</p>
            <p class="text-sm">Focus on your trading objectives and make informed decisions.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick reminders -->
    <div class="bg-yellow-50 rounded-lg p-6 border border-yellow-200">
      <h4 class="font-semibold text-yellow-900 mb-3 flex items-center">
        <LightBulbIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Quick Reminders
      </h4>
      <div class="grid gap-3 md:grid-cols-2 text-yellow-800 text-sm">
        <ul class="space-y-2 list-disc list-inside">
          <li>You can cancel orders before they execute</li>
          <li>Watch the order book for trading opportunities</li>
          <li>Keep track of your cash and share balances</li>
        </ul>
        <ul class="space-y-2 list-disc list-inside">
          <li>Consider both buying and selling strategies</li>
          <li>Pay attention to price movements</li>
          <li>Make decisions based on market conditions</li>
        </ul>
      </div>
    </div>

    <!-- Technical check -->
    <div class="bg-neutral-50 rounded-lg p-6 border border-neutral-200">
      <h4 class="font-semibold text-neutral-900 mb-3 flex items-center">
        <ComputerDesktopIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Technical Check
      </h4>
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-sm text-neutral-700">Internet Connection</span>
          <div class="flex items-center">
            <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            <span class="text-sm text-green-600">Connected</span>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-neutral-700">Browser Compatibility</span>
          <div class="flex items-center">
            <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            <span class="text-sm text-green-600">Compatible</span>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-neutral-700">WebSocket Support</span>
          <div class="flex items-center">
            <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            <span class="text-sm text-green-600">Supported</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Final confirmation -->
    <div class="space-y-4">
      <div class="bg-white border-2 border-green-200 rounded-lg p-6">
        <div class="text-center space-y-4">
          <h4 class="text-lg font-semibold text-neutral-900">
            Final Confirmation
          </h4>
          <p class="text-sm text-neutral-600">
            By proceeding, you confirm that you understand the trading rules, 
            have completed the preparation steps, and are ready to participate 
            in the live trading session.
          </p>
          
          <div class="flex items-center justify-center">
            <label class="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                v-model="ready"
                @change="$emit('update:ready', ready)"
                class="h-4 w-4 text-green-600 focus:ring-green-500 border-neutral-300 rounded"
              />
              <span class="text-sm text-neutral-700">
                I am ready to begin the live trading session
              </span>
            </label>
          </div>
        </div>
      </div>

      <!-- Support information -->
      <div class="text-center text-sm text-neutral-500">
        <p>
          If you encounter any issues during trading, look for help options 
          within the platform or contact the research team.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  RocketLaunchIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  ClockIcon,
  UsersIcon,
  ChartBarIcon,
  TrophyIcon,
  LightBulbIcon,
  ComputerDesktopIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  ready: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:ready'])

const ready = ref(props.ready)
</script> 