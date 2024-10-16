<template>
  <v-app>
    <v-app-bar app flat color="primary" dark>
      <v-container fluid class="py-0 fill-height">
        <v-row align="center" no-gutters>
          <v-col cols="auto">
            <h1 class="text-h5 font-weight-bold">
              <v-icon left color="light-blue" large>mdi-shield-account</v-icon>
              Admin Panel
            </h1>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto">
            <v-btn color="white" text :to="{ name: 'CreateTradingPlatform' }">
              Return to Create Session
            </v-btn>
          </v-col>
        </v-row>
      </v-container>
    </v-app-bar>

    <v-main class="grey lighten-4">
      <v-container fluid class="pa-4">
        <v-card class="mx-auto mt-5" elevation="2">
          <v-card-title class="headline">
            <v-icon left color="deep-blue">mdi-account-group</v-icon>
            Trading Session: {{ tradingSessionData.trading_session_uuid }}
          </v-card-title>
          <v-card-text>
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon left color="deep-blue">mdi-file-document-outline</v-icon>
                  Trading Session Creation Data
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="trader-data">{{ JSON.stringify(tradingSessionCreationData, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon left color="deep-blue">mdi-cog-outline</v-icon>
                  Trading Session Parameters
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-simple-table>
                    <template v-slot:default>
                      <thead>
                        <tr>
                          <th class="text-left">Parameter</th>
                          <th class="text-left">Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(value, key) in tradingSessionParameters" :key="key">
                          <td>{{ key }}</td>
                          <td>{{ value }}</td>
                        </tr>
                      </tbody>
                    </template>
                  </v-simple-table>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-row class="mt-4">
              <v-col v-for="(ht, ind) in tradingSessionData.human_traders" :key="ind" cols="12" sm="6" md="4">
                <v-card class="mb-4" elevation="2">
                  <v-card-title class="headline">
                    <v-icon left color="deep-blue">mdi-account</v-icon>
                    Trader {{ ind + 1 }}
                  </v-card-title>
                  <v-card-text>
                    <v-card 
                      @click="startTraderSession(ht.id)"
                      hover
                      class="trader-card mb-4"
                    >
                      <v-card-title class="title">
                        <v-icon left color="deep-blue">mdi-play-circle</v-icon>
                        Start Trader Session
                      </v-card-title>
                      <v-card-text>
                        <div class="font-weight-medium">Goal:</div>
                        <div>{{ ht.goal }}</div>
                      </v-card-text>
                    </v-card>
                    <v-card outlined>
                      <v-card-title class="title">
                        <v-icon left color="deep-blue">mdi-information-outline</v-icon>
                        Trader Data
                      </v-card-title>
                      <v-card-text>
                        <pre class="trader-data">{{ JSON.stringify(ht, null, 2) }}</pre>
                      </v-card-text>
                    </v-card>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
          
          <v-card-title class="headline">
            <v-icon left color="deep-blue">mdi-cog</v-icon>
            Persistent Settings
          </v-card-title>
          <v-card-text>
            <v-form @submit.prevent="savePersistentSettings">
              <v-row>
                <v-col cols="12" sm="6" v-for="(value, key) in editablePersistentSettings" :key="key">
                  <v-text-field
                    v-model="editablePersistentSettings[key]"
                    :label="key"
                    outlined
                    dense
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-btn color="primary" type="submit">Save Persistent Settings</v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { onMounted, computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";
import { useRouter } from 'vue-router';
import axios from '@/api/axios';

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
    numRounds: tradingSessionParameters.value.max_sessions_per_human
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

const editablePersistentSettings = ref({});

onMounted(async () => {
  await traderStore.getTraderAttributes(props.tradingSessionUUID);
  await fetchPersistentSettings();
});

const fetchPersistentSettings = async () => {
  try {
    const response = await axios.get('/admin/get_persistent_settings');
    editablePersistentSettings.value = response.data.data;
  } catch (error) {
    console.error('Error fetching persistent settings:', error);
  }
};

const savePersistentSettings = async () => {
  try {
    await axios.post('/admin/update_persistent_settings', {
      settings: editablePersistentSettings.value
    });
    alert('Persistent settings saved successfully');
  } catch (error) {
    console.error('Error saving persistent settings:', error);
    alert('Error saving persistent settings');
  }
};

</script>

<style scoped>
.trader-card {
  transition: all 0.3s;
  cursor: pointer;
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
  background-color: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
}
.headline {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
}
.title {
  font-size: 1.25rem;
  font-weight: 500;
  color: #2c3e50;
}
.deep-blue {
  color: #1a237e !important;
}
.light-blue {
  color: #03a9f4 !important;
}
</style>