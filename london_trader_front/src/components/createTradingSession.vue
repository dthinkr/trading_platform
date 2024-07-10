<template>
  <v-app app>
    <v-container class="fill-height">
      <v-row justify="center" align="center">
        <v-col cols="12">
          <v-form class="my-3">
            <v-row>
              <v-col v-for="(group, hint) in groupedFields" :key="hint" cols="12" sm="6" md="3">
                <v-card class="mb-4" height="100%">
                  <v-card-title class="text-capitalize">{{ hint.replace('_', ' ') }}</v-card-title>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" v-for="field in group" :key="field.name">
                        <v-text-field
                          :label="field.title || ''"
                          v-model="formState[field.name]"
                          :type="getFieldType(field)"
                          variant="outlined"
                          dense
                        ></v-text-field>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-form>
          <v-btn
            color="primary"
            block
            large
            @click="initializeTrader"
            :disabled="!serverActive"
          >{{ connectionServerMessage }}</v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-app>
</template>

<script setup>
import { onMounted, ref, computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import axios from "axios";

const httpUrl = import.meta.env.VITE_HTTP_URL;
const defaultsUrl = `${httpUrl}traders/defaults`;
const traderStore = useTraderStore();
const router = useRouter();
const serverActive = ref(false);
const connectionServerMessage = computed(() => {
  return serverActive.value
    ? "Connect to the server"
    : "Server is not available";
});
const formState = ref({});
const formFields = ref([]);

const { tradingSessionData } = storeToRefs(useTraderStore());

const initializeTrader = async () => {
  await traderStore.initializeTradingSystem(formState.value);
  router.push({
    name: "AdminPage",
    params: { tradingSessionUUID: tradingSessionData.value.trading_session_uuid }
  });
};

const groupedFields = computed(() => {
  const groups = {};
  formFields.value.forEach((field) => {
    const hint = field.hint || 'other';
    if (!groups[hint]) {
      groups[hint] = [];
    }
    groups[hint].push(field);
  });
  return groups;
});

const getFieldType = (field) => {
  if (!field || !field.type) return 'text';
  return ['number', 'integer'].includes(field.type) ? 'number' : 'text';
};

const fetchData = async () => {
  try {
    const response = await axios.get(defaultsUrl);
    const data = response.data.data;
    
    for (const [key, value] of Object.entries(data)) {
      formState.value[key] = value.default;
      formFields.value.push({ name: key, ...value });
    }
    serverActive.value = true;
  } catch (error) {
    serverActive.value = false;
    console.error("Failed to fetch form defaults:", error);
  }
};

onMounted(fetchData);
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}
</style>