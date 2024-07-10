<template>
  <v-app>
    <v-app-bar app flat color="primary" dark>
      <v-toolbar-title class="text-h6 font-weight-bold">Admin Panel</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn color="white" text :to="{ name: 'CreateTradingSession' }">
        Return to Create Session
      </v-btn>
    </v-app-bar>

    <v-main class="grey lighten-4">
      <v-container>
        <v-card class="mx-auto mt-5" max-width="900">
          <v-card-title class="text-h5 font-weight-bold primary white--text">
            Trading Session: {{ tradingSessionData.trading_session_uuid }}
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col v-for="(ht, ind) in tradingSessionData.human_traders" :key="ind" cols="12" sm="6" md="4">
                <v-card 
                  :to="`/trader/${ht.id}/landing`" 
                  target="_blank"
                  hover
                  class="trader-card"
                >
                  <v-card-title class="text-h6">
                    Trader {{ ind + 1 }}
                  </v-card-title>
                  <v-card-text>
                    <div class="font-weight-medium">Goal:</div>
                    <div>{{ ht.goal }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";

const props = defineProps({
  tradingSessionUUID: String,
});

const { tradingSessionData } = storeToRefs(useTraderStore());

console.log(tradingSessionData.value)

onMounted(() => {
  useTraderStore().getTradingSessionData(props.tradingSessionUUID);
});
</script>

<style scoped>
.trader-card {
  transition: all 0.3s;
}
.trader-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
</style>