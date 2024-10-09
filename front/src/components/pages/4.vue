<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div v-if="goalStatus !== 'noGoal'" class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-clock-alert</v-icon>
          Time Limit Not Met
        </h2>
        <p>If you do not achieve the objective within the time limit of the market, the trading platform will automatically execute additional trades.</p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-sale</v-icon>
          Trading Objective
        </h2>
        <p>{{ goalDescription }}</p>
        <div v-if="goalStatus !== 'noGoal' && goalStatus !== 'unknown'" class="highlight-box info">
          <v-icon color="iconColor">mdi-information</v-icon>
          <p>At the end of the market, the trading platform will automatically {{ tradeAction.toLowerCase() }} each {{ tradeAction === 'Selling' ? 'unsold' : 'unbought' }} share (if any) at a price equal to {{ autoTradeMultiplier }} the average best bid and ask price (mid-price) at the end of each market.</p>
        </div>
        <p v-if="goalStatus !== 'noGoal' && goalStatus !== 'unknown'" class="mt-3">
          Loosely speaking, {{ autoTradeMultiplier }} the market price at the end of the market.
        </p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-calculator</v-icon>
          Market Earnings Calculation
        </h2>
        <div class="highlight-box success">
          <v-icon color="iconColor">mdi-cash</v-icon>
          <div>
            <p class="font-weight-bold">Market earnings =</p>
            <p v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'">
              Net profit or loss from all trades
            </p>
            <p v-else-if="goalStatus === 'selling'">
              Revenue from sales <span class="formula-note">(incl. automatically sold shares)</span>
              <br>− <span class="formula-highlight">(Number of shares)</span> × <span class="formula-highlight">(Mid-price at the beginning of the market)</span>
            </p>
            <p v-else>
              <span class="formula-highlight">(Number of shares)</span> × <span class="formula-highlight">(Mid-price at the beginning of the market)</span>
              <br>− Cost of purchases <span class="formula-note">(incl. automatically bought shares)</span>
            </p>
          </div>
        </div>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">{{ goalStatus === 'noGoal' ? 'mdi-information' : (tradeAction === 'Selling' ? 'mdi-arrow-down-bold' : 'mdi-arrow-up-bold') }}</v-icon>
          {{ goalStatus === 'noGoal' ? 'Market Dynamics' : `Trading Objective` }}
        </h2>
        <p v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'">
          The market price may fluctuate above or below the mid-price at the beginning of the market. These fluctuations can lead to potential gains or losses on your trades.
        </p>
        <p v-else>
          Your task is to {{ tradeAction.toLowerCase() }} <span class="dynamic-value">{{ Math.abs(numShares) }} shares</span>.
          The market price might {{ tradeAction === 'Selling' ? 'drop below' : 'rise above' }} the mid-price at the beginning of the market.
          If that happens, each {{ tradeAction.toLowerCase() }} of a share will {{ tradeAction === 'Selling' ? 'make a loss' : 'make a profit' }}.
        </p>
        <div class="highlight-box info">
          <v-icon color="iconColor">{{ goalStatus === 'noGoal' ? 'mdi-information' : (tradeAction === 'Selling' ? 'mdi-arrow-down-bold' : 'mdi-arrow-up-bold') }}</v-icon>
          <p>
            {{ goalStatus === 'noGoal' || goalStatus === 'unknown'
              ? 'Your success will depend on your ability to analyze market conditions and make informed trading decisions.'
              : (tradeAction === 'Selling' 
                ? 'However, selling the shares is still in your interest as keeping them would create an even more significant loss.' 
                : 'However, buying the shares is still in your interest as not buying them would create an even more significant loss.')
            }}
          </p>
        </div>
        <p class="mt-3">
          <span v-if="goalStatus === 'noGoal'">
            You will be given <span class="dynamic-value">{{ initialLiras }} Liras</span> and <span class="dynamic-value">{{ numShares }} shares</span> at the beginning of the market.
          </span>
          <span v-else-if="tradeAction === 'Selling'">
            You will be given <span class="dynamic-value">{{ Math.abs(numShares) }} shares</span> at the beginning of the market.
          </span>
          <span v-else>
            You will be given <span class="dynamic-value">{{ initialLiras }} Liras</span> at the beginning of the market to facilitate your purchases.
          </span>
        </p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon :color="iconColor">mdi-cash</v-icon>
          Final Earnings
        </h2>
        <p>At the end of the study, you will be awarded earnings from one randomly selected market.</p>
        <div class="highlight-box info">
          <v-icon color="iconColor">mdi-swap-horizontal</v-icon>
          <p>Your earnings in the chosen market will be calculated in Liras. These Liras will then be converted into GBP and paid to you. The conversion rate is <span class="dynamic-value">{{ conversionRate }} Liras = 1 GBP</span>.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";

const props = defineProps({
  traderAttributes: Object,
  iconColor: String
});

const traderStore = useTraderStore();
const { goalMessage } = storeToRefs(traderStore);

const numShares = computed(() => props.traderAttributes?.shares ?? '#');
const initialLiras = computed(() => props.traderAttributes?.cash ?? '#');
const conversionRate = computed(() => props.traderAttributes?.all_attributes?.params?.conversion_rate || 'X');

const goalStatus = computed(() => {
  if (props.traderAttributes?.shares === undefined) return 'unknown';
  if (props.traderAttributes?.shares === props.traderAttributes?.initial_shares) return 'noGoal';
  return props.traderAttributes?.shares < props.traderAttributes?.initial_shares ? 'selling' : 'buying';
});

const tradeAction = computed(() => {
  if (goalStatus.value === 'selling') return 'Selling';
  if (goalStatus.value === 'buying') return 'Buying';
  return 'Trading';
});

const autoTradeMultiplier = computed(() => {
  if (goalStatus.value === 'selling') return '½×';
  if (goalStatus.value === 'buying') return '1.5×';
  return '';
});

const goalDescription = computed(() => {
  if (!goalMessage.value) return 'Your trading goal is currently being determined...';
  return goalMessage.value.text;
});
</script>

<style scoped>
.formula-highlight {
  font-weight: bold;
}

.formula-note {
  font-size: 0.9em;
  font-style: italic;
}
</style>