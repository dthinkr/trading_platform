<template>
  <div class="card-content">    
    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-desktop-mac</v-icon>
        What is the Trading Platform?
      </v-card-title>
      <v-card-text class="text-h5">
        The trading platform is software that allows you to trade with other participants. It shows relevant information about the demand and supply of an asset (e.g. a share). What you see on the trading platform is common knowledge i.e. all other participants can see it.
      </v-card-text>
    </v-card>


    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-handshake</v-icon>
        Placing Orders
      </v-card-title>
      <v-card-text class="text-h5">
        You can buy or sell shares by placing orders. We call a buy order a "bid" and a sell order an "ask".
      </v-card-text>
      
      <v-divider class="mx-4"></v-divider>
      
      <v-row class="pa-4">
        <v-col cols="12" md="6">
          <v-card outlined>
            <v-card-title class="text-h5 success--text">
              <v-icon left color="success">mdi-flash</v-icon>
              Direct Orders
            </v-card-title>
            <v-card-text class="text-h5">
              You can directly accept an existing price to sell or buy, such as an order from another participant. In this case, the trade is immediately executed at the best bid or ask respectively.
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card outlined>
            <v-card-title class="text-h5 info--text">
              <v-icon left color="info">mdi-clock</v-icon>
              Passive Orders
            </v-card-title>
            <v-card-text class="text-h5">
              You can place orders to sell or buy that are not immediately executed. This means you have to wait for someone who will accept them.
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card>

    <v-card class="mb-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-trending-up</v-icon>
        Improving Orders
      </v-card-title>
      <v-card-text>
        <v-list>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="success">mdi-arrow-down</v-icon>
            </v-list-item-icon>
            <v-list-item-content class="text-h6">
              Place an order to sell (ask) a share for a lower price than the current best ask (selling price)
            </v-list-item-content>
          </v-list-item>
          <v-list-item>
            <v-list-item-icon>
              <v-icon color="error">mdi-arrow-up</v-icon>
            </v-list-item-icon>
            <v-list-item-content class="text-h6">
              Place an order to buy (bid) a share for a higher price than the current best bid (buying price)
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card class="mt-6" elevation="3" shaped>
      <v-card-title class="text-h5 font-weight-bold primary--text">
        <v-icon left color="primary">mdi-image</v-icon>
        Trading Platform Demo
      </v-card-title>
      <v-card-text class="text-h5">
        <p class="mb-4">
          Here's a demonstration of the trading platform in action:
        </p>
        <v-img
  src="../../assets/demo.gif"
  alt="Trading Platform Demo"
  max-width="600"
  class="mx-auto"
></v-img>
        <p class="mt-4 font-italic">
          This GIF shows the key features of the trading platform, including real-time updates and order placement.
        </p>
      </v-card-text>
    </v-card>
  </div>
</template>