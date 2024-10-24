<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-help-circle</v-icon>
          Control Questions
        </h2>
        <p class="mb-4">Please answer these questions to ensure you understand the trading rules:</p>

        <v-list>
          <v-list-item v-for="(question, index) in questions" :key="index" class="mb-4">
            <v-list-item-content>
              <v-list-item-title class="mb-2 wrap-text">{{ question.text }}</v-list-item-title>
              <v-radio-group 
                v-model="question.userAnswer" 
                @change="checkAnswer(index)"
                :disabled="question.isCorrect"
              >
                <v-radio
                  v-for="option in question.options"
                  :key="option"
                  :label="option"
                  :value="option"
                  :color="getRadioColor(question, option)"
                ></v-radio>
              </v-radio-group>
              
              <v-alert
                v-if="question.showFeedback && !question.isCorrect"
                type="error"
                class="mt-2"
                dense
              >
                Incorrect. The correct answer is: {{ question.correctAnswer }}
                <div class="mt-2">{{ question.explanation }}</div>
              </v-alert>

              <v-alert
                v-if="question.isCorrect"
                type="success"
                class="mt-2"
                dense
              >
                Correct!
              </v-alert>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  iconColor: String
});

const router = useRouter();

// Initialize all questions as not correct
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
  }
]);

const allQuestionsAnsweredCorrectly = computed(() => {
  return questions.value.every(q => q.isCorrect);
});

// Emit event to parent to control Next button state
const emit = defineEmits(['update:canProgress']);

// Watch for changes in allQuestionsAnsweredCorrectly
watch(allQuestionsAnsweredCorrectly, (newValue) => {
  emit('update:canProgress', newValue);
});

// Also emit initial state on mount
onMounted(() => {
  emit('update:canProgress', false);
});

const checkAnswer = (index) => {
  const question = questions.value[index];
  question.showFeedback = true;
  question.isCorrect = question.userAnswer === question.correctAnswer;
  // Emit the updated state after each answer
  emit('update:canProgress', allQuestionsAnsweredCorrectly.value);
};

const getRadioColor = (question, option) => {
  if (!question.showFeedback) return 'primary';
  if (option === question.correctAnswer) return 'success';
  if (option === question.userAnswer && !question.isCorrect) return 'error';
  return 'primary';
};
</script>

<style scoped>
.wrap-text {
  white-space: normal;
  word-wrap: break-word;
}

.v-list-item {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 1rem;
  padding: 1rem;
}

.v-radio-group {
  margin-top: 0.5rem;
}

.v-alert {
  margin-top: 0.5rem;
}
</style>
