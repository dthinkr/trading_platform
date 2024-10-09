<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-robot</v-icon>
          Artificial Traders
        </h2>
        <p>The other participants in the market are all artificial (algorithmic) traders, i.e., non-human.</p>
        <v-alert
          color="info"
          border="start"
          elevation="2"
          colored-border
          icon="mdi-information"
          class="mt-3"
          icon-color="grey darken-1"
        >
          All artificial traders have no objective in terms of earnings.
        </v-alert>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-refresh</v-icon>
          Trader Behavior
        </h2>
        <v-list>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="iconColor">mdi-login</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              Artificial traders randomly join the market for a short period
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="iconColor">mdi-swap-horizontal</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              They buy and sell during their time in the market
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="iconColor">mdi-logout</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              They are then replaced by other artificial traders
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-chart-line</v-icon>
          Market Activity
        </h2>
        <p>These traders ensure activity in the market that enables you to buy and sell.</p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-school</v-icon>
          Next Steps
        </h2>
        <v-list>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="iconColor">mdi-checkbox-marked-circle</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="font-weight-bold">Control Questions</v-list-item-title>
              <v-list-item-subtitle>You will answer some control questions</v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="iconColor">mdi-checkbox-marked-circle</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="font-weight-bold">Practice Session</v-list-item-title>
              <v-list-item-subtitle>You will practice trading to familiarize yourself with the trading platform</v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  iconColor: String
});
</script>