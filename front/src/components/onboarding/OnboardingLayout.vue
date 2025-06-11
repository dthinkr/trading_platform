<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
    <!-- Skip to main content -->
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 btn btn-primary">
      Skip to main content
    </a>

    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-neutral-200">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <ChartBarIcon class="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <h1 class="text-lg font-semibold text-neutral-900">Trading Platform</h1>
          </div>
          
          <!-- Progress indicator -->
          <div class="flex items-center space-x-2">
            <span class="text-sm text-neutral-600">
              Step {{ currentStep }} of {{ totalSteps }}
            </span>
            <div class="w-24 bg-neutral-200 rounded-full h-2">
              <div 
                class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                :style="{ width: `${(currentStep / totalSteps) * 100}%` }"
                role="progressbar"
                :aria-valuenow="currentStep"
                :aria-valuemax="totalSteps"
                aria-label="Onboarding progress"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main content -->
    <main id="main-content" class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="bg-white rounded-xl shadow-lg border border-neutral-200 overflow-hidden">
        
        <!-- Step header -->
        <div class="px-6 py-4 bg-neutral-50 border-b border-neutral-200">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-xl font-semibold text-neutral-900">{{ stepTitle }}</h2>
              <p v-if="stepDescription" class="text-sm text-neutral-600 mt-1">
                {{ stepDescription }}
              </p>
            </div>
            <div v-if="showTimer && timeRemaining" class="text-right">
              <span class="text-sm text-neutral-600">Time remaining:</span>
              <div class="text-lg font-semibold text-blue-600">
                {{ formatTime(timeRemaining) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Step content -->
        <div class="p-6">
          <slot />
        </div>

        <!-- Navigation -->
        <div class="px-6 py-4 bg-neutral-50 border-t border-neutral-200">
          <div class="flex items-center justify-between">
            <button
              v-if="showBackButton && currentStep > 1"
              @click="goBack"
              class="btn btn-outline flex items-center"
              :disabled="isNavigating"
            >
              <ArrowLeftIcon class="h-4 w-4 mr-2" />
              Back
            </button>
            <div v-else></div> <!-- Spacer -->

            <div class="flex items-center space-x-3">
              <button
                v-if="showSkipButton"
                @click="skipStep"
                class="btn btn-ghost text-neutral-600"
                :disabled="isNavigating"
              >
                Skip
              </button>
              
              <button
                @click="goNext"
                :disabled="!canProceed || isNavigating"
                :class="[
                  'btn flex items-center',
                  canProceed ? 'btn-primary' : 'btn-outline opacity-50 cursor-not-allowed'
                ]"
              >
                <span v-if="isNavigating" class="spinner h-4 w-4 mr-2"></span>
                {{ nextButtonText }}
                <ArrowRightIcon v-if="!isNavigating" class="h-4 w-4 ml-2" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Help text -->
      <div v-if="helpText" class="mt-4 text-center">
        <p class="text-sm text-neutral-600">{{ helpText }}</p>
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-16 py-8 border-t border-neutral-200">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center text-sm text-neutral-500">
          <p>Having trouble? Contact support or check the help documentation.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { 
  ChartBarIcon, 
  ArrowLeftIcon, 
  ArrowRightIcon 
} from '@heroicons/vue/24/outline'

const props = defineProps({
  currentStep: {
    type: Number,
    required: true
  },
  totalSteps: {
    type: Number,
    required: true
  },
  stepTitle: {
    type: String,
    required: true
  },
  stepDescription: {
    type: String,
    default: ''
  },
  canProceed: {
    type: Boolean,
    default: true
  },
  isNavigating: {
    type: Boolean,
    default: false
  },
  showBackButton: {
    type: Boolean,
    default: true
  },
  showSkipButton: {
    type: Boolean,
    default: false
  },
  showTimer: {
    type: Boolean,
    default: false
  },
  timeRemaining: {
    type: Number,
    default: null
  },
  nextButtonText: {
    type: String,
    default: 'Continue'
  },
  helpText: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['next', 'back', 'skip'])

// Methods
function goNext() {
  if (props.canProceed && !props.isNavigating) {
    emit('next')
  }
}

function goBack() {
  if (!props.isNavigating) {
    emit('back')
  }
}

function skipStep() {
  if (!props.isNavigating) {
    emit('skip')
  }
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}
</script> 