<template>
  <div class="card-content">

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-help-circle</v-icon>
        True or False Questions
      </v-card-title>
      <v-card-text>
        <v-list>
          <v-list-item v-for="(question, index) in trueOrFalseQuestions" :key="index">
            <v-list-item-content>
              <v-list-item-title class="text-h5 mb-2 wrap-text">{{ question.text }}</v-list-item-title>
              <v-radio-group v-model="question.answer" row>
                <v-radio label="Correct" value="correct"></v-radio>
                <v-radio label="Incorrect" value="incorrect"></v-radio>
              </v-radio-group>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="secondary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-calculator</v-icon>
        Calculation Questions
      </v-card-title>
      <v-card-text>
        <v-list>
          <v-list-item v-for="(question, index) in calculationQuestions" :key="index">
            <v-list-item-content>
              <v-list-item-title class="text-h5 mb-2 wrap-text">{{ question.text }}</v-list-item-title>
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
      </v-card-text>
    </v-card>

    <v-card class="mt-6" elevation="3" shaped color="success" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-school</v-icon>
        Practice Session
      </v-card-title>
      <v-card-text class="text-h5">
        After answering these control questions, you will have a practice session to familiarize yourself with the trading platform.
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref } from 'vue';

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
    text: `Let us assume a market is selected in which you had the task of selling all your 10 shares and you received 50 Lira at the start. You sold all the 10 shares for an average price of 11. The price at the beginning of the market was 12. What would be your earnings in Lira at the end of this market?`,
    answer: null,
    options: ['100 Lira', '110 Lira', '120 Lira', '500 Lira']
  },
  { 
    text: `Let us assume a market is selected in which you had the task of buying 10 shares and you received 60 Lira at the start. You bought 10 shares for an average price of 11. The price at the beginning of the market was 10. What would be your earnings in Lira at the end of this market?`,
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