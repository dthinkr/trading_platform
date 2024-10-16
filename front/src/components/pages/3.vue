<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-information-outline</v-icon>
          Overview
        </h2>
        <p>We are going to conduct <span class="dynamic-value">{{ numMarkets }} markets</span> in which you will be a participant. You have a straightforward task:</p>
        <div class="highlight-box warning">
          <v-icon color="warning">mdi-alert</v-icon>
          <p>The task is to sell all your shares OR buy a given number. At the beginning of each market we will tell you to sell OR buy a given number of shares. You can only buy OR sell shares not both.</p>
        </div>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-target</v-icon>
          Your Objective
        </h2>
        <p>Sell at the highest price or buy at the lowest price.</p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-clock-outline</v-icon>
          Market Details
        </h2>
        <p>All trading will be in terms of Liras and the length of each market will be <span class="dynamic-value">{{ marketDuration }} minutes</span>.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useTraderStore } from "@/store/app";

const props = defineProps({
  iconColor: String
});

const traderStore = useTraderStore();

const marketDuration = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.trading_day_duration || 0;
});

const numMarkets = computed(() => {
  return traderStore.traderAttributes?.all_attributes?.params?.max_sessions_per_human || 0;
});
</script>

<style scoped>
.custom-list {
  list-style-type: none;
  padding-left: 0;
  margin-bottom: 0;
}

.custom-list li {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.custom-list li .v-icon {
  margin-right: 0.5rem;
}

.highlight-box p {
  margin-bottom: 0;
}
</style>