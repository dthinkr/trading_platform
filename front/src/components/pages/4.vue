<template>
  <div class="card-content">
    <!-- New card to display attributes in plain text -->
    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-text-box-outline</v-icon>
        Trader Attributes (Plain Text)
      </v-card-title>
      <v-card-text>
        <pre>{{ JSON.stringify(traderStore, null, 2) }}</pre>
      </v-card-text>
    </v-card>

    <v-card v-if="goalStatus !== 'noGoal'" class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left color="warning">mdi-clock-alert</v-icon>
        Time Limit Not Met
      </v-card-title>
      <v-card-text class="text-h5">
        If you do not achieve the objective within the time limit of the market, the trading platform will automatically execute additional trades.
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-sale</v-icon>
        {{ goalStatus === 'noGoal' ? 'Trading Objective' : `Automatic ${tradeAction}` }}
      </v-card-title>
      <v-card-text class="text-h5">
        <p v-if="goalStatus === 'noGoal'">You have no specific buying or selling goal for this session. Your objective is to trade based on market conditions and your own strategy.</p>
        <p v-else-if="goalStatus === 'unknown'">Your trading goal is currently being determined...</p>
        <p v-else>Your task is to {{ tradeAction.toLowerCase() }} <span class="dynamic-value">{{ Math.abs(numShares) }} shares</span>:</p>
        <v-alert
          v-if="goalStatus !== 'noGoal' && goalStatus !== 'unknown'"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-information"
          class="mt-3"
        >
          At the end of the market, the trading platform will automatically {{ tradeAction.toLowerCase() }} each {{ tradeAction === 'Selling' ? 'unsold' : 'unbought' }} share (if any) at a price equal to {{ autoTradeMultiplier }} the average best bid and ask price (mid-price) at the end of each market.
        </v-alert>
        <p v-if="goalStatus !== 'noGoal' && goalStatus !== 'unknown'" class="mt-3">
          Loosely speaking, {{ autoTradeMultiplier }} the market price at the end of the market.
        </p>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left color="success">mdi-calculator</v-icon>
        Market Earnings Calculation
      </v-card-title>
      <v-card-text class="text-h5">
        <v-alert
          color="success"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-cash"
          class="mb-3"
        >
          <div class="text-h6 font-weight-bold mb-2">Market earnings =</div>
          <div class="pl-4" v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'">
            Net profit or loss from all trades
          </div>
          <div class="pl-4" v-else-if="goalStatus === 'selling'">
            Revenue from sales <span class="formula-note">(incl. automatically sold shares)</span>
            <br>− <span class="formula-highlight">(Number of shares)</span> × <span class="formula-highlight">(Mid-price at the beginning of the market)</span>
          </div>
          <div class="pl-4" v-else>
            <span class="formula-highlight">(Number of shares)</span> × <span class="formula-highlight">(Mid-price at the beginning of the market)</span>
            <br>− Cost of purchases <span class="formula-note">(incl. automatically bought shares)</span>
          </div>
        </v-alert>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>{{ goalStatus === 'noGoal' ? 'mdi-information' : (tradeAction === 'Selling' ? 'mdi-arrow-down-bold' : 'mdi-arrow-up-bold') }}</v-icon>
        {{ goalStatus === 'noGoal' ? 'Market Dynamics' : `Trading Objective` }}
      </v-card-title>
      <v-card-text class="text-h5">
        <p v-if="goalStatus === 'noGoal' || goalStatus === 'unknown'">
          The market price may fluctuate above or below the mid-price at the beginning of the market. These fluctuations can lead to potential gains or losses on your trades.
        </p>
        <p v-else>
          Your task is to {{ tradeAction.toLowerCase() }} <span class="dynamic-value">{{ Math.abs(numShares) }} shares</span>.
          The market price might {{ tradeAction === 'Selling' ? 'drop below' : 'rise above' }} the mid-price at the beginning of the market.
          If that happens, each {{ tradeAction.toLowerCase() }} of a share will {{ tradeAction === 'Selling' ? 'make a loss' : 'make a profit' }}.
        </p>
        <v-alert
          border="left"
          elevation="2"
          colored-border
          :icon="goalStatus === 'noGoal' ? 'mdi-information' : (tradeAction === 'Selling' ? 'mdi-arrow-down-bold' : 'mdi-arrow-up-bold')"
          class="mt-3"
        >
          {{ goalStatus === 'noGoal' || goalStatus === 'unknown'
            ? 'Your success will depend on your ability to analyze market conditions and make informed trading decisions.'
            : (tradeAction === 'Selling' 
              ? 'However, selling the shares is still in your interest as keeping them would create an even more significant loss.' 
              : 'However, buying the shares is still in your interest as not buying them would create an even more significant loss.')
          }}
        </v-alert>
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
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="secondary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-currency-gbp</v-icon>
        Final Earnings
      </v-card-title>
      <v-card-text class="text-h5">
        <p>At the end of the study, you will be awarded earnings from one randomly selected market.</p>
        <v-alert
          border="left"
          elevation="2"
          colored-border
          icon="mdi-swap-horizontal"
          class="mt-3"
        >
          Your earnings in the chosen market will be calculated in Liras. These Liras will then be converted into GBP and paid to you. The conversion rate is <span class="dynamic-value">{{ conversionRate }} Liras = 1 GBP</span>.
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  traderAttributes: Object
});

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

console.log('Trader attributes in 4.vue:', props.traderAttributes); // Debug log
</script>

<style scoped>
.dynamic-value {
  display: inline-block;
  padding: 2px 6px;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-weight: 500;
}

.formula-highlight {
  font-weight: bold;
}

.formula-note {
  font-size: 0.9em;
  font-style: italic;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>