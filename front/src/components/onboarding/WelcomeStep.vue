<template>
  <div class="space-y-6">
    <!-- Welcome message -->
    <div class="text-center">
      <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <HandshakeIcon class="h-8 w-8 text-blue-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Welcome to the Trading Research Study
      </h3>
      <p class="text-lg text-neutral-600">
        Thank you for participating in our trading platform research study
      </p>
    </div>

    <!-- Study information -->
    <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
      <h4 class="font-semibold text-blue-900 mb-3 flex items-center">
        <InformationCircleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        About This Study
      </h4>
      <div class="space-y-3 text-blue-800">
        <p>
          This research study examines trading behavior in simulated financial markets. 
          You will participate in a trading session where you can buy and sell shares.
        </p>
        <ul class="list-disc list-inside space-y-1 text-sm">
          <li>The session typically lasts 15-30 minutes</li>
          <li>You'll start with virtual cash and shares</li>
          <li>Your goal may be to maximize profit or achieve specific trading targets</li>
          <li>All trading is simulated - no real money is involved</li>
        </ul>
      </div>
    </div>

    <!-- Terms and conditions -->
    <div class="border border-neutral-200 rounded-lg">
      <div class="p-4 bg-neutral-50 border-b border-neutral-200">
        <h4 class="font-semibold text-neutral-900 flex items-center">
          <DocumentTextIcon class="h-5 w-5 mr-2" aria-hidden="true" />
          Terms and Conditions
        </h4>
      </div>
      
      <div class="p-4 max-h-64 overflow-y-auto text-sm text-neutral-700 space-y-3">
        <div>
          <h5 class="font-medium text-neutral-900 mb-1">Participation</h5>
          <p>
            By participating in this study, you acknowledge that you are voluntarily 
            taking part in research and that you may withdraw at any time without penalty.
          </p>
        </div>
        
        <div>
          <h5 class="font-medium text-neutral-900 mb-1">Data Collection</h5>
          <p>
            We will collect data about your trading decisions, timing, and interactions 
            with the platform. This data is used solely for research purposes and will 
            be anonymized.
          </p>
        </div>
        
        <div>
          <h5 class="font-medium text-neutral-900 mb-1">Confidentiality</h5>
          <p>
            Your personal information and trading data will be kept confidential and 
            will not be shared with third parties. Published results will not contain 
            any personally identifiable information.
          </p>
        </div>
        
        <div>
          <h5 class="font-medium text-neutral-900 mb-1">Compensation</h5>
          <p>
            Compensation details, if any, have been communicated to you separately. 
            Trading performance in this simulation does not affect your compensation 
            unless specifically stated otherwise.
          </p>
        </div>
        
        <div>
          <h5 class="font-medium text-neutral-900 mb-1">Technical Requirements</h5>
          <p>
            Please ensure you have a stable internet connection and can remain focused 
            during the trading session. If you experience technical difficulties, 
            please contact the researcher immediately.
          </p>
        </div>
      </div>
    </div>

    <!-- Consent checkbox -->
    <div class="space-y-4">
      <div class="flex items-start">
        <div class="flex items-center h-5">
          <input
            id="consent-checkbox"
            v-model="agreed"
            type="checkbox"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-neutral-300 rounded"
            @change="$emit('update:agreed', agreed)"
          />
        </div>
        <div class="ml-3">
          <label for="consent-checkbox" class="text-sm text-neutral-700">
            I have read and understood the terms and conditions above. I consent to 
            participate in this research study and understand that I may withdraw at any time.
          </label>
        </div>
      </div>
      
      <div v-if="!agreed" class="text-xs text-neutral-500">
        You must agree to the terms and conditions to proceed with the study.
      </div>
    </div>

    <!-- Contact information -->
    <div class="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
      <h4 class="font-semibold text-neutral-900 mb-2 flex items-center">
        <PhoneIcon class="h-4 w-4 mr-2" aria-hidden="true" />
        Need Help?
      </h4>
      <p class="text-sm text-neutral-600">
        If you have questions about this study or experience any technical issues, 
        please contact the research team or use the help features available in the platform.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  HandshakeIcon,
  InformationCircleIcon,
  DocumentTextIcon,
  PhoneIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  agreed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:agreed'])

// Local state
const agreed = ref(props.agreed)
</script> 