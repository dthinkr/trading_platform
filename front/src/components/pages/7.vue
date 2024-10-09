<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-help-circle</v-icon>
          True or False Questions
        </h2>
        <v-list>
          <v-list-item v-for="(question, index) in trueOrFalseQuestions" :key="index">
            <v-list-item-content>
              <v-list-item-title class="mb-2 wrap-text">{{ question.text }}</v-list-item-title>
              <v-radio-group v-model="question.answer" row>
                <v-radio label="Correct" value="correct"></v-radio>
                <v-radio label="Incorrect" value="incorrect"></v-radio>
              </v-radio-group>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-calculator</v-icon>
          Calculation Questions
        </h2>
        <v-list>
          <v-list-item v-for="(question, index) in calculationQuestions" :key="index">
            <v-list-item-content>
              <v-list-item-title class="mb-2 wrap-text">{{ question.text }}</v-list-item-title>
              <v-radio-group v-model="question.answer" column>
                <v-radio
                  v-for="(option, optionIndex) in question.options"
                  :key="optionIndex"
                  :label="option"
                  :value="option"
                ></v-radio>
              </v-radio-group>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-school</v-icon>
          Practice Session
        </h2>
        <p>After answering these control questions, you will have a practice session to familiarize yourself with the trading platform.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  iconColor: String
});

const trueOrFalseQuestions = ref([
  { text: "You can both buy and sell shares.", answer: null },
  { text: "You must always improve an existing bid (buy order) or ask (sell order).", answer: null },
  { text: "All other traders are artificial?", answer: null },
  { text: "Do the shares you own at the end of the market pay a dividend?", answer: null },
  { text: "Your task is either to sell or buy shares. To maximise your earnings you must complete the task.", answer: null },
  { text: "Your earnings are the sum of the earnings in all markets.", answer: null },
]);

const calculationQuestions = ref([
  { 
    text: "Let us assume a market is selected in which you had the task of selling all your 10 shares and you received 50 Lira at the start. You sold all the 10 shares for an average price of 11. The price at the beginning of the market was 12. What would be your earnings in Lira at the end of this market?",
    answer: null,
    options: ['100 Lira', '110 Lira', '120 Lira', '500 Lira']
  },
  { 
    text: "Let us assume a market is selected in which you had the task of buying 10 shares and you received 60 Lira at the start. You bought 10 shares for an average price of 11. The price at the beginning of the market was 10. What would be your earnings in Lira at the end of this market?",
    answer: null,
    options: ['100 Lira', '110 Lira', '120 Lira', '600 Lira']
  },
]);
</script>

<style scoped>
.wrap-text {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>