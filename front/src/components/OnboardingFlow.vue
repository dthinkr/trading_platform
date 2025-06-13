<template>
  <OnboardingLayout
    :current-step="currentStep"
    :total-steps="totalSteps"
    :step-title="currentStepData.title"
    :step-description="currentStepData.description"
    :can-proceed="canProceed"
    :is-navigating="isNavigating"
    :show-back-button="currentStep > 1"
    :show-skip-button="currentStepData.skippable"
    :show-timer="showTimer"
    :time-remaining="timeRemaining"
    :next-button-text="currentStepData.nextButtonText"
    :help-text="currentStepData.helpText"
    @next="handleNext"
    @back="handleBack"
    @skip="handleSkip"
  >
    <!-- Welcome Step -->
    <WelcomeStep 
      v-if="currentStep === 1"
      v-model:agreed="steps.welcome.agreed"
      @update:agreed="updateCanProceed"
    />

    <!-- Instructions Step -->
    <InstructionsStep 
      v-else-if="currentStep === 2"
      v-model:understood="steps.instructions.understood"
      @update:understood="updateCanProceed"
    />

    <!-- Practice Step -->
    <PracticeStep 
      v-else-if="currentStep === 3"
      v-model:completed="steps.practice.completed"
      @update:completed="updateCanProceed"
    />

    <!-- Quiz Step -->
    <QuizStep 
      v-else-if="currentStep === 4"
      v-model:passed="steps.quiz.passed"
      @update:passed="updateCanProceed"
    />

    <!-- Ready Step -->
    <ReadyStep 
      v-else-if="currentStep === 5"
      v-model:ready="steps.ready.ready"
      @update:ready="updateCanProceed"
    />
  </OnboardingLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTradingStore } from '@/stores/trading'
import axios from '@/api/axios'

import OnboardingLayout from './onboarding/OnboardingLayout.vue'
import WelcomeStep from './onboarding/WelcomeStep.vue'
import InstructionsStep from './onboarding/InstructionsStep.vue'
import PracticeStep from './onboarding/PracticeStep.vue'
import QuizStep from './onboarding/QuizStep.vue'
import ReadyStep from './onboarding/ReadyStep.vue'

const router = useRouter()
const authStore = useAuthStore()
const tradingStore = useTradingStore()

// State
const currentStep = ref(1)
const isNavigating = ref(false)
const showTimer = ref(false)
const timeRemaining = ref(null)

// Step data and progress tracking
const steps = ref({
  welcome: { agreed: false },
  instructions: { understood: false },
  practice: { completed: false },
  quiz: { passed: false },
  ready: { ready: false }
})

const totalSteps = 5

const stepConfig = {
  1: {
    title: 'Welcome to the Trading Platform',
    description: 'Please read and agree to the terms before proceeding',
    nextButtonText: 'I Agree → Continue',
    skippable: false,
    helpText: 'You must agree to the terms to participate in the trading session'
  },
  2: {
    title: 'Trading Instructions',
    description: 'Learn how the trading platform works',
    nextButtonText: 'I Understand → Next',
    skippable: false,
    helpText: 'Understanding the trading mechanics is essential for participation'
  },
  3: {
    title: 'Practice Trading',
    description: 'Try placing some practice orders to get familiar with the interface',
    nextButtonText: 'Complete Practice → Next',
    skippable: true,
    helpText: 'Practice is recommended but you can skip if you\'re already familiar'
  },
  4: {
    title: 'Knowledge Quiz',
    description: 'Answer a few questions to confirm your understanding',
    nextButtonText: 'Submit Quiz → Next',
    skippable: false,
    helpText: 'You must pass the quiz to ensure you understand the trading rules'
  },
  5: {
    title: 'Ready to Trade',
    description: 'Final confirmation before entering the live trading session',
    nextButtonText: 'Enter Trading Session →',
    skippable: false,
    helpText: 'Once you proceed, the live trading session will begin'
  }
}

const currentStepData = computed(() => stepConfig[currentStep.value])

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 1: return steps.value.welcome.agreed
    case 2: return steps.value.instructions.understood
    case 3: return steps.value.practice.completed
    case 4: return steps.value.quiz.passed
    case 5: return steps.value.ready.ready
    default: return false
  }
})

// Methods
function updateCanProceed() {
  // This function is called when child components update their completion status
  // The computed property will automatically update
}

async function handleNext() {
  console.log('handleNext called - currentStep:', currentStep.value, 'canProceed:', canProceed.value)
  
  if (!canProceed.value || isNavigating.value) {
    console.log('Cannot proceed - canProceed:', canProceed.value, 'isNavigating:', isNavigating.value)
    return
  }

  isNavigating.value = true

  try {
    if (currentStep.value === totalSteps) {
      // Final step - navigate to trading
      console.log('Completing onboarding...')
      await completeOnboarding()
    } else {
      // Move to next step
      const oldStep = currentStep.value
      currentStep.value++
      console.log('Moving from step', oldStep, 'to step', currentStep.value)
      await saveProgress()
    }
  } catch (error) {
    console.error('Error proceeding to next step:', error)
    // Handle error appropriately
  } finally {
    isNavigating.value = false
  }
}

function handleBack() {
  console.log('handleBack called - currentStep:', currentStep.value)
  
  if (currentStep.value > 1 && !isNavigating.value) {
    const oldStep = currentStep.value
    currentStep.value--
    console.log('Moving back from step', oldStep, 'to step', currentStep.value)
    saveProgress()
  }
}

function handleSkip() {
  if (currentStepData.value.skippable && !isNavigating.value) {
    // Mark step as completed for skippable steps
    if (currentStep.value === 3) {
      steps.value.practice.completed = true
    }
    currentStep.value++
    saveProgress()
  }
}

async function completeOnboarding() {
  try {
    console.log('Starting onboarding completion...')
    
    // Mark onboarding as complete
    await authStore.completeOnboarding()
    console.log('Onboarding marked as complete')
    
    // Navigate to waiting room instead of directly to trading
    console.log('Navigating to waiting room...')
    router.push('/waiting-room')
  } catch (error) {
    console.error('Failed to complete onboarding:', error)
    // Still navigate to waiting room even if backend call fails
    router.push('/waiting-room')
  }
}

async function saveProgress() {
  try {
    // Save current progress to backend or localStorage
    const progress = {
      currentStep: currentStep.value,
      completedSteps: steps.value,
      timestamp: new Date().toISOString()
    }
    
    localStorage.setItem('onboarding-progress', JSON.stringify(progress))
    
    // Could also save to backend if needed
    // await authStore.saveOnboardingProgress(progress)
  } catch (error) {
    console.error('Failed to save progress:', error)
  }
}

function loadProgress() {
  try {
    const saved = localStorage.getItem('onboarding-progress')
    if (saved) {
      const progress = JSON.parse(saved)
      
      // Only restore if it's from today (prevent stale progress)
      const savedDate = new Date(progress.timestamp)
      const today = new Date()
      if (savedDate.toDateString() === today.toDateString()) {
        currentStep.value = progress.currentStep
        steps.value = { ...steps.value, ...progress.completedSteps }
      }
    }
  } catch (error) {
    console.error('Failed to load progress:', error)
  }
}

// Lifecycle
onMounted(() => {
  loadProgress()
  
  // Check if user should be here
  if (authStore.hasCompletedOnboarding) {
    router.push('/trading')
  }
})

// Auto-save progress when leaving
onUnmounted(() => {
  saveProgress()
})
</script> 