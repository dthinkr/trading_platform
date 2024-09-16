<template>
  <v-app>
    <v-app-bar app flat color="primary" dark>
      <v-toolbar-title class="text-h6 font-weight-bold">Admin Panel</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn color="white" text :to="{ name: 'CreateTradingPlatform' }">
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
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  Trading Session Creation Data
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="trader-data">{{ JSON.stringify(tradingSessionCreationData, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  Trading Session Parameters
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table>
                    <template v-slot:default>
                      <thead>
                        <tr>
                          <th>Parameter</th>
                          <th>Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(value, key) in tradingSessionParameters" :key="key">
                          <td>{{ key }}</td>
                          <td>{{ value }}</td>
                        </tr>
                      </tbody>
                    </template>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-row class="mt-4">
              <v-col v-for="(ht, ind) in tradingSessionData.human_traders" :key="ind" cols="12">
                <v-card class="mb-4">
                  <v-card-title class="text-h6">
                    Trader {{ ind + 1 }}
                  </v-card-title>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" sm="6">
                        <v-card 
                          @click="startTraderSession(ht.id)"
                          hover
                          class="trader-card"
                        >
                          <v-card-title class="text-h6">
                            Start Trader Session
                          </v-card-title>
                          <v-card-text>
                            <div class="font-weight-medium">Goal:</div>
                            <div>{{ ht.goal }}</div>
                          </v-card-text>
                        </v-card>
                      </v-col>
                      <v-col cols="12" sm="6">
                        <v-card outlined>
                          <v-card-title class="text-h6">
                            Trader Data
                          </v-card-title>
                          <v-card-text>
                            <pre class="trader-data">{{ JSON.stringify(ht, null, 2) }}</pre>
                          </v-card-text>
                        </v-card>
                      </v-col>
                    </v-row>
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
import { onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";
import { useRouter } from 'vue-router';

const props = defineProps({
  tradingSessionUUID: String,
});

const router = useRouter();
const traderStore = useTraderStore();
const { tradingSessionData, formState } = storeToRefs(traderStore);

const tradingSessionCreationData = computed(() => {
  const { human_traders, ...rest } = tradingSessionData.value;
  return rest;
});

const tradingSessionParameters = computed(() => {
  return formState.value || {};
});

const startTraderSession = (traderId) => {
  const params = {
    traderUuid: traderId,
    duration: tradingSessionParameters.value.trading_day_duration,
    numRounds: tradingSessionParameters.value.num_rounds
  };
  router.push({ 
    name: 'onboarding',  // Change this from 'TraderLanding' to 'onboarding'
    params: { 
      traderUuid: params.traderUuid,
      duration: params.duration,
      numRounds: params.numRounds
    } 
  });
};

console.log("tradingSessionData:", tradingSessionData.value);
console.log("formState:", formState.value);

onMounted(async () => {
  await traderStore.getTraderAttributes(props.tradingSessionUUID);
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
.trader-data {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.8rem;
  max-height: 300px;
  overflow-y: auto;
}
</style>