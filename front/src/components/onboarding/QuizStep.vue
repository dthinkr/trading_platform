<template>
  <div class="space-y-6">
    <!-- Quiz header -->
    <div class="text-center">
      <div class="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <AcademicCapIcon class="h-8 w-8 text-indigo-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Knowledge Check
      </h3>
      <p class="text-lg text-neutral-600">
        Answer these questions to confirm your understanding of the trading rules
      </p>
    </div>

    <!-- Progress Summary (non-restrictive) -->
    <div class="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-indigo-900">Progress</span>
        <span class="text-sm text-indigo-700">{{ correctAnswers }} of {{ questions.length }} correct</span>
      </div>
      <p class="text-xs text-indigo-600 mt-1">
        Answer all questions correctly to proceed
      </p>
    </div>

    <!-- All Questions Grid -->
    <div class="grid gap-6 lg:grid-cols-2">
      <div
        v-for="(question, index) in questions"
        :key="index"
        class="bg-white border border-neutral-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
        :class="{
          'border-green-300 bg-green-50': question.isCorrect,
          'border-red-300 bg-red-50': question.showFeedback && !question.isCorrect
        }"
      >
        <!-- Question Header -->
        <div class="bg-neutral-50 px-4 py-3 border-b border-neutral-200">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold text-neutral-900">
              Question {{ index + 1 }}
            </h4>
            <div v-if="question.isCorrect" class="flex items-center space-x-1">
              <CheckCircleIcon class="h-4 w-4 text-green-600" />
              <span class="text-xs text-green-700 font-medium">Correct</span>
            </div>
          </div>
        </div>
        
        <!-- Question Content -->
        <div class="p-4">
          <!-- Question text -->
          <p class="text-neutral-900 font-medium mb-4">
            {{ question.text }}
          </p>
          
          <!-- Answer options -->
          <div class="space-y-2">
            <label
              v-for="(option, optionIndex) in question.options"
              :key="optionIndex"
              class="flex items-start space-x-3 cursor-pointer p-2 rounded border transition-colors"
              :class="[
                question.userAnswer === option 
                  ? 'border-indigo-300 bg-indigo-50' 
                  : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50',
                question.showFeedback && option === question.correctAnswer && 'border-green-300 bg-green-50',
                question.showFeedback && option === question.userAnswer && !question.isCorrect && 'border-red-300 bg-red-50'
              ]"
            >
              <input
                type="radio"
                :value="option"
                v-model="question.userAnswer"
                @change="checkAnswer(index)"
                :disabled="question.isCorrect"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-neutral-300 mt-0.5"
              />
              <span class="text-sm text-neutral-700">{{ option }}</span>
            </label>
          </div>
          
          <!-- Feedback -->
          <div v-if="question.showFeedback" class="mt-4 p-3 rounded-lg"
               :class="[
                 question.isCorrect 
                   ? 'bg-green-50 border border-green-200' 
                   : 'bg-red-50 border border-red-200'
               ]">
            <div class="flex items-start">
              <component 
                :is="question.isCorrect ? CheckCircleIcon : XCircleIcon"
                :class="[
                  'h-4 w-4 mr-2 mt-0.5 flex-shrink-0',
                  question.isCorrect ? 'text-green-600' : 'text-red-600'
                ]"
              />
              <div>
                <p :class="[
                  'font-medium text-xs',
                  question.isCorrect ? 'text-green-800' : 'text-red-800'
                ]">
                  {{ question.isCorrect ? 'Correct!' : 'Incorrect' }}
                </p>
                <p :class="[
                  'text-xs mt-1',
                  question.isCorrect ? 'text-green-700' : 'text-red-700'
                ]">
                  {{ question.explanation }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Completion Status -->
    <div v-if="allQuestionsAnsweredCorrectly" class="flex items-center justify-center">
      <div class="flex items-center space-x-3 p-4 bg-green-50 border border-green-200 rounded-lg">
        <CheckCircleIcon class="h-5 w-5 text-green-600" />
        <span class="text-sm text-green-800 font-medium">
          Excellent! All questions answered correctly. You may proceed to the next step.
        </span>
      </div>
    </div>

    <!-- Retry hint if not all correct -->
    <div v-else-if="hasAnsweredQuestions" class="text-center">
      <p class="text-sm text-neutral-600">
        Please answer all questions correctly to proceed. You can change your answers at any time.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  AcademicCapIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  passed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:passed'])

// Quiz questions from prolific-new branch
const questions = ref([
  {
    text: "If you have a certain buying or selling goal, can you both buy and sell shares in the same market?",
    options: ["Yes", "No"],
    correctAnswer: "No",
    explanation: "You can only buy OR sell shares in a given market, not both.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  },
  {
    text: "What happens when you place a passive order?",
    options: [
      "It executes immediately",
      "You must wait for someone to accept it",
      "It gets automatically cancelled"
    ],
    correctAnswer: "You must wait for someone to accept it",
    explanation: "Passive orders wait in the order book until another trader accepts them.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  },
  {
    text: "How many shares can you trade in a single order?",
    options: [
      "As many as you want",
      "Only one share per order",
      "Maximum of 10 shares"
    ],
    correctAnswer: "Only one share per order",
    explanation: "Each order is for one share only. If you want to trade multiple shares, you need to place multiple orders.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  },
  {
    text: "What happens if you don't complete your trading objective within the time limit?",
    options: [
      "Nothing happens",
      "The system automatically completes the trades for you",
      "You lose all your earnings"
    ],
    correctAnswer: "The system automatically completes the trades for you",
    explanation: "The trading platform will automatically execute any remaining required trades at the end of the market.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  },
  {
    text: "What are the other market participants?",
    options: [
      "Human Participants",
      "Artificial (Algorithmic) Agents",
      "Both"
    ],
    correctAnswer: "Artificial (Algorithmic) Agents",
    explanation: "In this experimental session, you will play only with artificial agents.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  },
  {
    text: "What is the impact on the market price if one of the artificial agents sells a large number of shares?",
    options: [
      "Mid-Price increases",
      "Mid-Price decreases",
      "Mid-Price remains constant"
    ],
    correctAnswer: "Mid-Price decreases",
    explanation: "In this scenario, the price of the new best buy offer will decrease, and consequently, the mid-price will also decrease.",
    userAnswer: null,
    isCorrect: false,
    showFeedback: false
  }
])

// Computed properties
const correctAnswers = computed(() => {
  return questions.value.filter(q => q.isCorrect).length
})

const allQuestionsAnsweredCorrectly = computed(() => {
  return questions.value.every(q => q.isCorrect)
})

const hasAnsweredQuestions = computed(() => {
  return questions.value.some(q => q.userAnswer !== null)
})

// Methods
function checkAnswer(index) {
  const question = questions.value[index]
  if (!question.userAnswer) return
  
  question.showFeedback = true
  question.isCorrect = question.userAnswer === question.correctAnswer
  
  // Emit updated pass status
  emit('update:passed', allQuestionsAnsweredCorrectly.value)
}
</script> 