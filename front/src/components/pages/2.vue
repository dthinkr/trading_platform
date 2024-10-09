<template>
  <div class="card-content">
    <div class="content-wrapper">
      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-monitor</v-icon>
          What is the Trading Platform?
        </h2>
        <p>The trading platform is software that allows you to trade with other participants. It shows relevant information about the demand and supply of an asset (e.g. a share). What you see on the trading platform is common knowledge i.e. all other participants can see it.</p>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-handshake</v-icon>
          Placing Orders
        </h2>
        <p>You can buy or sell shares by placing orders. We call a buy order a "bid" and a sell order an "ask".</p>
        
        <v-divider class="my-4"></v-divider>
        
        <div class="d-flex justify-space-between">
          <div class="flex-grow-1 mr-2">
            <h3 class="success--text">
              <v-icon left color="success">mdi-flash</v-icon>
              Direct Orders
            </h3>
            <p>You can directly accept an existing price to sell or buy, such as an order from another participant. In this case, the trade is immediately executed at the best bid or ask respectively.</p>
          </div>
          <div class="flex-grow-1 ml-2">
            <h3 class="info--text">
              <v-icon left color="info">mdi-clock</v-icon>
              Passive Orders
            </h3>
            <p>You can place orders to sell or buy that are not immediately executed. This means you have to wait for someone who will accept them.</p>
          </div>
        </div>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-trending-up</v-icon>
          Improving Orders
        </h2>
        <ul class="custom-list">
          <li>
            <v-icon color="success">mdi-arrow-down</v-icon>
            Place an order to sell (ask) a share for a lower price than the current best ask (selling price)
          </li>
          <li>
            <v-icon color="error">mdi-arrow-up</v-icon>
            Place an order to buy (bid) a share for a higher price than the current best bid (buying price)
          </li>
        </ul>
      </div>

      <div class="info-section">
        <h2>
          <v-icon left :color="iconColor">mdi-image</v-icon>
          Trading Platform Demo
        </h2>
        <p class="mb-4">Here's a demonstration of the trading platform in action:</p>
        <v-img
          :src="demoGif"
          alt="Trading Platform Demo"
          max-width="600"
          contain
          class="mx-auto"
        ></v-img>
        <p class="mt-4 font-italic">This GIF shows the key features of the trading platform, including real-time updates and order placement.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import demoGif from '@/assets/demo.gif';

const props = defineProps({
  iconColor: String
});
</script>

<style scoped>
.custom-list {
  list-style-type: none;
  padding-left: 0;
}

.custom-list li {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.custom-list li .v-icon {
  margin-right: 0.5rem;
}
</style>