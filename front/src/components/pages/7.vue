<template>
  <div class="questions-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="36" :color="iconColor" class="pulse-icon">mdi-brain</v-icon>
        <h2 class="text-h4 gradient-text">Knowledge Check</h2>
        <div class="progress-indicator">
          <div class="progress-text">{{ correctCount }}/{{ questions.length }} Correct</div>
          <v-progress-linear
            :model-value="(correctCount / questions.length) * 100"
            color="success"
            height="8"
            rounded
            striped
          ></v-progress-linear>
        </div>
      </div>
    </v-scale-transition>

    <v-container class="questions-grid">
      <v-row>
        <v-col v-for="(question, index) in questions" 
               :key="index" 
               cols="12" 
               :md="questions.length <= 2 ? 12 : 6"
               class="question-col">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 8 : 2"
              :class="['question-card', {
                'correct': question.isCorrect,
                'incorrect': question.showFeedback && !question.isCorrect
              }]"
              :color="getCardColor(question)"
              transition="scale-transition"
            >
              <v-slide-y-transition>
                <v-card-text>
                  <div class="question-number">#{{ index + 1 }}</div>
                  <div class="question-text">{{ question.text }}</div>
                  
                  <v-fade-transition group>
                    <v-radio-group
                      v-model="question.userAnswer"
                      @change="checkAnswer(index)"
                      :disabled="question.isCorrect"
                      class="options-group"
                      density="compact"
                    >
                      <v-radio
                        v-for="option in question.options"
                        :key="option"
                        :label="option"
                        :value="option"
                        :color="getRadioColor(question, option)"
                        class="option-radio"
                      ></v-radio>
                    </v-radio-group>
                  </v-fade-transition>

                  <v-expand-transition>
                    <div v-if="question.showFeedback" class="feedback-section">
                      <v-alert
                        :type="question.isCorrect ? 'success' : 'error'"
                        :text="question.isCorrect ? 'Correct!' : question.explanation"
                        class="feedback-alert"
                        variant="tonal"
                        density="compact"
                      ></v-alert>
                    </div>
                  </v-expand-transition>
                </v-card-text>
              </v-slide-y-transition>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  iconColor: String
});

const router = useRouter();

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

const correctCount = computed(() => {
  return questions.value.filter(q => q.isCorrect).length;
});

const allQuestionsAnsweredCorrectly = computed(() => {
  return questions.value.every(q => q.isCorrect);
});

const emit = defineEmits(['update:canProgress']);

watch(allQuestionsAnsweredCorrectly, (newValue) => {
  emit('update:canProgress', newValue);
});

onMounted(() => {
  emit('update:canProgress', false);
});

const checkAnswer = (index) => {
  const question = questions.value[index];
  question.showFeedback = true;
  question.isCorrect = question.userAnswer === question.correctAnswer;
  emit('update:canProgress', allQuestionsAnsweredCorrectly.value);
};

const getRadioColor = (question, option) => {
  if (!question.showFeedback) return 'primary';
  if (option === question.correctAnswer) return 'success';
  if (option === question.userAnswer && !question.isCorrect) return 'error';
  return 'grey';
};

const getCardColor = (question) => {
  if (!question.showFeedback) return 'surface';
  return question.isCorrect ? 'success-lighten-4' : 'error-lighten-4';
};
</script>

<style scoped>
.questions-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header-section {
  text-align: center;
  margin-bottom: 2rem;
  position: relative;
}

.gradient-text {
  background: linear-gradient(45deg, #2196F3, #4CAF50);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
  margin: 1rem 0;
}

.pulse-icon {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.progress-indicator {
  max-width: 300px;
  margin: 1rem auto;
}

.progress-text {
  text-align: center;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #666;
}

.question-card {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
}

.question-number {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0,0,0,0.1);
  padding: 0.3rem 0.8rem;
  border-radius: 1rem;
  font-weight: bold;
}

.question-text {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 1.5rem 0;
  padding-right: 3rem;
}

.options-group {
  margin-top: 1rem;
}

.option-radio {
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.option-radio:hover {
  transform: translateX(5px);
}

.feedback-section {
  margin-top: 1rem;
}

.feedback-alert {
  margin: 0;
  transition: all 0.3s ease;
}

.question-col {
  transition: all 0.3s ease;
}

@media (max-width: 960px) {
  .questions-container {
    padding: 1rem;
  }
  
  .question-text {
    font-size: 1rem;
  }
}
</style>
