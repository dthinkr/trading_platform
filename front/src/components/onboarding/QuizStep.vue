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
        Answer these questions to confirm your understanding
      </p>
    </div>

    <!-- Progress -->
    <div class="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-indigo-900">Progress</span>
        <span class="text-sm text-indigo-700">{{ currentQuestion + 1 }} of {{ questions.length }}</span>
      </div>
      <div class="w-full bg-indigo-200 rounded-full h-2">
        <div 
          class="bg-indigo-600 h-2 rounded-full transition-all duration-300"
          :style="{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }"
        ></div>
      </div>
    </div>

    <!-- Current Question -->
    <div v-if="!quizCompleted" class="bg-white border border-neutral-200 rounded-lg overflow-hidden">
      <div class="bg-neutral-50 px-6 py-4 border-b border-neutral-200">
        <h4 class="text-lg font-semibold text-neutral-900">
          Question {{ currentQuestion + 1 }}
        </h4>
      </div>
      
      <div class="p-6">
        <div class="space-y-4">
          <!-- Question text -->
          <p class="text-neutral-900 font-medium">
            {{ questions[currentQuestion].question }}
          </p>
          
          <!-- Answer options -->
          <div class="space-y-3">
            <label
              v-for="(option, index) in questions[currentQuestion].options"
              :key="index"
              class="flex items-start space-x-3 cursor-pointer p-3 rounded-lg border transition-colors"
              :class="[
                selectedAnswer === index 
                  ? 'border-indigo-300 bg-indigo-50' 
                  : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
              ]"
            >
              <input
                type="radio"
                :value="index"
                v-model="selectedAnswer"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-neutral-300 mt-0.5"
              />
              <span class="text-sm text-neutral-700">{{ option }}</span>
            </label>
          </div>
          
          <!-- Show explanation after answering -->
          <div v-if="showExplanation" class="mt-4 p-4 rounded-lg"
               :class="[
                 isCorrect 
                   ? 'bg-green-50 border border-green-200' 
                   : 'bg-red-50 border border-red-200'
               ]">
            <div class="flex items-start">
              <component 
                :is="isCorrect ? CheckCircleIcon : XCircleIcon"
                :class="[
                  'h-5 w-5 mr-2 mt-0.5',
                  isCorrect ? 'text-green-600' : 'text-red-600'
                ]"
              />
              <div>
                <p :class="[
                  'font-medium text-sm',
                  isCorrect ? 'text-green-800' : 'text-red-800'
                ]">
                  {{ isCorrect ? 'Correct!' : 'Incorrect' }}
                </p>
                <p :class="[
                  'text-sm mt-1',
                  isCorrect ? 'text-green-700' : 'text-red-700'
                ]">
                  {{ questions[currentQuestion].explanation }}
                </p>
              </div>
            </div>
          </div>
          
          <!-- Navigation buttons -->
          <div class="flex justify-between pt-4">
            <button
              v-if="currentQuestion > 0"
              @click="previousQuestion"
              class="btn btn-outline"
              :disabled="showExplanation"
            >
              Previous
            </button>
            <div v-else></div>
            
            <button
              v-if="!showExplanation"
              @click="checkAnswer"
              :disabled="selectedAnswer === null"
              class="btn btn-primary"
            >
              Check Answer
            </button>
            
            <button
              v-else-if="currentQuestion < questions.length - 1"
              @click="nextQuestion"
              class="btn btn-primary"
            >
              Next Question
            </button>
            
            <button
              v-else
              @click="completeQuiz"
              class="btn btn-primary"
            >
              Complete Quiz
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quiz Results -->
    <div v-if="quizCompleted" class="space-y-6">
      <!-- Results summary -->
      <div class="text-center">
        <div :class="[
          'w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4',
          quizPassed ? 'bg-green-100' : 'bg-red-100'
        ]">
          <component 
            :is="quizPassed ? CheckCircleIcon : XCircleIcon"
            :class="[
              'h-8 w-8',
              quizPassed ? 'text-green-600' : 'text-red-600'
            ]"
          />
        </div>
        <h4 :class="[
          'text-xl font-bold mb-2',
          quizPassed ? 'text-green-900' : 'text-red-900'
        ]">
          {{ quizPassed ? 'Quiz Passed!' : 'Quiz Not Passed' }}
        </h4>
        <p :class="[
          'text-sm',
          quizPassed ? 'text-green-700' : 'text-red-700'
        ]">
          You scored {{ correctAnswers }} out of {{ questions.length }} questions correctly
          ({{ Math.round((correctAnswers / questions.length) * 100) }}%)
        </p>
      </div>

      <!-- Detailed results -->
      <div :class="[
        'rounded-lg p-6 border',
        quizPassed ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
      ]">
        <h5 :class="[
          'font-semibold mb-3',
          quizPassed ? 'text-green-900' : 'text-red-900'
        ]">
          Question Review
        </h5>
        <div class="space-y-3">
          <div
            v-for="(question, index) in questions"
            :key="index"
            class="flex items-start space-x-3 text-sm"
          >
            <component 
              :is="userAnswers[index] === question.correct ? CheckCircleIcon : XCircleIcon"
              :class="[
                'h-4 w-4 mt-0.5 flex-shrink-0',
                userAnswers[index] === question.correct ? 'text-green-600' : 'text-red-600'
              ]"
            />
            <div>
              <p class="font-medium text-neutral-900">{{ question.question }}</p>
              <p :class="[
                'text-xs',
                userAnswers[index] === question.correct ? 'text-green-700' : 'text-red-700'
              ]">
                Your answer: {{ question.options[userAnswers[index]] }}
                <span v-if="userAnswers[index] !== question.correct">
                  (Correct: {{ question.options[question.correct] }})
                </span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Retry option if failed -->
      <div v-if="!quizPassed" class="text-center">
        <button
          @click="retakeQuiz"
          class="btn btn-primary"
        >
          Retake Quiz
        </button>
        <p class="text-sm text-neutral-600 mt-2">
          You need to score at least 70% to proceed. Review the explanations and try again.
        </p>
      </div>
    </div>

    <!-- Pass confirmation -->
    <div v-if="quizPassed" class="flex items-center justify-center">
      <div class="flex items-center space-x-3">
        <CheckCircleIcon class="h-5 w-5 text-green-600" />
        <span class="text-sm text-neutral-700 font-medium">
          Quiz completed successfully! You may proceed to the next step.
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
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

// Quiz state
const currentQuestion = ref(0)
const selectedAnswer = ref(null)
const showExplanation = ref(false)
const userAnswers = ref([])
const quizCompleted = ref(false)

// Quiz questions
const questions = ref([
  {
    question: "What is the 'spread' in an order book?",
    options: [
      "The total number of shares available for trading",
      "The difference between the highest bid price and lowest ask price", 
      "The average price of all recent trades",
      "The maximum number of shares you can buy"
    ],
    correct: 1,
    explanation: "The spread is the difference between the best bid (highest buy offer) and best ask (lowest sell offer) prices."
  },
  {
    question: "If you place a buy order at $100 and the current best ask is $102, what will happen?",
    options: [
      "Your order will execute immediately at $100",
      "Your order will execute immediately at $102",
      "Your order will be added to the order book and wait for a seller at $100",
      "Your order will be rejected"
    ],
    correct: 2,
    explanation: "Since your bid ($100) is lower than the best ask ($102), your order will be added to the order book and wait for a matching seller."
  },
  {
    question: "What does 'P&L' stand for in trading?",
    options: [
      "Price and Limit",
      "Profit and Loss",
      "Purchase and Liquidation",
      "Portfolio and Leverage"
    ],
    correct: 1,
    explanation: "P&L stands for Profit and Loss, which shows how much money you've made or lost from your trading activities."
  },
  {
    question: "When should you consider cancelling an order?",
    options: [
      "Never, all orders should be left to execute",
      "Only when you've made a mistake in the price",
      "When market conditions change or you want to adjust your strategy",
      "Only at the end of the trading session"
    ],
    correct: 2,
    explanation: "You might cancel orders when market conditions change, you want to adjust your strategy, or place orders at different prices."
  },
  {
    question: "What happens if you try to sell more shares than you own?",
    options: [
      "The system will automatically buy shares for you first",
      "You can sell them and go into negative share holdings",
      "The order will be rejected or limited to your available shares",
      "The shares will be borrowed from other traders"
    ],
    correct: 2,
    explanation: "In most trading systems, you cannot sell more shares than you own. The system will reject such orders or limit them to your available holdings."
  }
])

// Computed properties
const correctAnswers = computed(() => {
  return userAnswers.value.filter((answer, index) => 
    answer === questions.value[index].correct
  ).length
})

const quizPassed = computed(() => {
  const passingScore = Math.ceil(questions.value.length * 0.7) // 70% pass rate
  return quizCompleted.value && correctAnswers.value >= passingScore
})

const isCorrect = computed(() => {
  return selectedAnswer.value === questions.value[currentQuestion.value].correct
})

// Methods
function checkAnswer() {
  if (selectedAnswer.value === null) return
  
  userAnswers.value[currentQuestion.value] = selectedAnswer.value
  showExplanation.value = true
}

function nextQuestion() {
  if (currentQuestion.value < questions.value.length - 1) {
    currentQuestion.value++
    selectedAnswer.value = userAnswers.value[currentQuestion.value] ?? null
    showExplanation.value = false
  }
}

function previousQuestion() {
  if (currentQuestion.value > 0) {
    currentQuestion.value--
    selectedAnswer.value = userAnswers.value[currentQuestion.value] ?? null
    showExplanation.value = userAnswers.value[currentQuestion.value] !== undefined
  }
}

function completeQuiz() {
  quizCompleted.value = true
}

function retakeQuiz() {
  currentQuestion.value = 0
  selectedAnswer.value = null
  showExplanation.value = false
  userAnswers.value = []
  quizCompleted.value = false
}

// Watch for quiz completion and emit
watch(quizPassed, (newValue) => {
  emit('update:passed', newValue)
})
</script> 