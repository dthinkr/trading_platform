<template>
  <div class="card-content">

    <v-card class="mb-6" elevation="3" shaped color="secondary" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-robot</v-icon>
        Artificial Traders
      </v-card-title>
      <v-card-text class="text-h5">
        <p>The other participants in the market are all artificial (algorithmic) traders, i.e., non-human.</p>
        <v-alert
          color="info"
          border="left"
          elevation="2"
          colored-border
          icon="mdi-information"
          class="mt-3"
        >
          All artificial traders have no objective in terms of earnings.
        </v-alert>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-refresh</v-icon>
        Trader Behavior
      </v-card-title>
      <v-card-text class="text-h5">
        <v-list>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="green">mdi-login</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              Artificial traders randomly join the market for a short period
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="blue">mdi-swap-horizontal</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              They buy and sell during their time in the market
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="red">mdi-logout</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              They are then replaced by other artificial traders
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped color="success" dark>
      <v-card-title class="text-h5 font-weight-bold">
        <v-icon left>mdi-chart-line</v-icon>
        Market Activity
      </v-card-title>
      <v-card-text class="text-h5">
        These traders ensure activity in the market that enables you to buy and sell.
      </v-card-text>
    </v-card>

  <v-card class="mb-6" elevation="3" shaped>
    <v-card-title class="text-h5 font-weight-bold primary--text">
      <v-icon left color="primary">mdi-school</v-icon>
      Next Steps
    </v-card-title>
    <v-card-text class="text-h5">
      <v-list>
        <v-list-item>
          <v-list-item-icon>
            <v-icon color="primary">mdi-checkbox-marked-circle</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title class="font-weight-bold">Control Questions</v-list-item-title>
            <v-list-item-subtitle>You will answer some control questions</v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
        <v-list-item>
          <v-list-item-icon>
            <v-icon color="green">mdi-checkbox-marked-circle</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title class="font-weight-bold">Practice Session</v-list-item-title>
            <v-list-item-subtitle>You will practice trading to familiarize yourself with the trading platform</v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
  </div>
</template>