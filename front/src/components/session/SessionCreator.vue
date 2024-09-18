<template>
  <v-container fluid class="fill-height">
    <v-row>
      <v-col cols="12" md="8">
        <v-card class="mb-4">
          <v-card-title class="text-h5 font-weight-bold">Create Trading Session</v-card-title>
          <v-card-text>
            <v-form>
              <div class="parameter-grid">
                <v-card v-for="(group, hint) in groupedFields" :key="hint" outlined class="parameter-card" :class="{ 'parameter-card-large': group.length > 4 }">
                  <v-card-title class="text-capitalize subtitle-1">{{ hint.replace('_', ' ') }}</v-card-title>
                  <v-card-text>
                    <v-row dense>
                      <v-col cols="12" v-for="field in group" :key="field.name">
                        <v-text-field
                          v-if="!isArrayField(field)"
                          :label="field.title || ''"
                          v-model="formState[field.name]"
                          :type="getFieldType(field)"
                          dense
                          outlined
                          hide-details="auto"
                          class="mb-2 short-input"
                          @input="updatePersistentSettings"
                        ></v-text-field>
                        <v-text-field
                          v-else
                          :label="field.title || ''"
                          v-model="formState[field.name]"
                          dense
                          outlined
                          hide-details="auto"
                          class="mb-2 short-input"
                          @input="handleArrayInput(field.name, $event)"
                        ></v-text-field>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </div>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" @click="saveSettings" :disabled="!serverActive">Save Settings</v-btn>
            <v-btn color="secondary" @click="startExperiment" :disabled="!serverActive">Start in Background</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card class="mb-4">
          <v-card-title class="text-h5 font-weight-bold">Session Manager</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item v-for="session in sessions" :key="session.id">
                <v-list-item-title class="font-weight-medium">Session ID: {{ session.id.slice(0, 8) }}...</v-list-item-title>
                <v-list-item-subtitle>Status: {{ session.status }}</v-list-item-subtitle>
                <template #append>
                  <v-row class="mt-2">
                    <v-col cols="6">
                      <v-btn
                        :disabled="session.status !== 'finished'"
                        @click="downloadCombinedCSV(session.id)"
                        color="primary"
                        small
                        outlined
                        block
                      >
                        Download CSV
                      </v-btn>
                    </v-col>
                    <v-col cols="6">
                      <v-btn
                        :disabled="session.status !== 'finished'"
                        @click="showResult(session.id)"
                        color="secondary"
                        small
                        outlined
                        block
                      >
                        Show Result
                      </v-btn>
                    </v-col>
                  </v-row>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="showResultDialog" @click:outside="closeResultDialog" max-width="1200px">
      <v-card v-if="selectedSession">
        <v-card-title class="text-h5">
          Session Results
          <v-spacer></v-spacer>
          <v-btn icon @click="closeResultDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <h3>Parameters</h3>
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(value, key) in selectedSession.parameters" :key="key">
                    <td>{{ key }}</td>
                    <td>{{ value }}</td>
                  </tr>
                </tbody>
              </v-table>
            </v-col>
            <v-col cols="12" md="6">
              <h3>End Metrics</h3>
              <v-table density="compact" v-if="selectedSession.endMetrics">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(value, key) in selectedSession.endMetrics" :key="key">
                    <td>{{ key }}</td>
                    <td>{{ value }}</td>
                  </tr>
                </tbody>
              </v-table>
              <p v-else>No end metrics available</p>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12">
              <h3>Session Plot</h3>
              <div v-if="svgPlot" v-html="svgPlot" class="session-plot"></div>
              <p v-else>No plot available</p>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useTraderStore } from "@/store/app";
import axios from 'axios';
import Papa from 'papaparse';

const traderStore = useTraderStore();
const formState = ref({});
const formFields = ref([]);
const serverActive = ref(false);
const sessions = ref([]);
const svgPlot = ref('');
const selectedSession = ref(null);
const showResultDialog = ref(false);

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

const isArrayField = (field) => {
  return field.type === 'array';
};

const handleArrayInput = (fieldName, value) => {
  if (value === '') {
    formState.value[fieldName] = [];
  } else {
    formState.value[fieldName] = value.split(',').map(item => item.trim());
  }
  updatePersistentSettings();
};

const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`)
    ]);

    const defaultData = defaultsResponse.data.data;
    const persistentSettings = persistentSettingsResponse.data.data;

    for (const [key, value] of Object.entries(defaultData)) {
      formState.value[key] = persistentSettings[key] || value.default;
      formFields.value.push({ name: key, ...value });
    }
    serverActive.value = true;
  } catch (error) {
    serverActive.value = false;
    console.error("Failed to fetch form defaults or persistent settings:", error);
  }
};

const updatePersistentSettings = async () => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, {
      settings: formState.value
    });
  } catch (error) {
    console.error("Failed to update persistent settings:", error);
    throw error; // Re-throw the error so it can be caught in the saveSettings function
  }
};

const saveSettings = async () => {
  try {
    await updatePersistentSettings();
    // You can add a success message or notification here
    console.log("Settings saved successfully");
  } catch (error) {
    console.error("Error saving settings:", error);
    // You can add an error message or notification here
  }
};

const startExperiment = async () => {
  try {
    const response = await axios.post(`${import.meta.env.VITE_HTTP_URL}experiment/start`, formState.value);
    const sessionId = response.data.data.trading_session_uuid;
    const duration = formState.value.duration;
    sessions.value.push({ 
      id: sessionId, 
      status: 'running', 
      duration,
      parameters: { ...formState.value }
    });
    setTimeout(() => checkExperimentStatus(sessionId), duration * 60 * 1000);
  } catch (error) {
    console.error("Error starting experiment:", error);
  }
};

const checkExperimentStatus = async (sessionId) => {
  const checkStatus = async () => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/status/${sessionId}`);
      const session = sessions.value.find(s => s.id === sessionId);
      if (session) {
        session.status = response.data.data.is_finished ? 'finished' : 'running';
        if (response.data.data.is_finished) {
          // Fetch end metrics when session is finished
          const endMetricsResponse = await axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/end_metrics/${sessionId}`);
          session.endMetrics = endMetricsResponse.data.data;
        } else {
          setTimeout(checkStatus, 10000);
        }
      }
    } catch (error) {
      console.error("Error checking experiment status:", error);
    }
  };

  checkStatus();
};

const downloadCombinedCSV = async (sessionId) => {
  try {
    const [endMetricsResponse, timeSeriesMetricsResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/end_metrics/${sessionId}`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/time_series_metrics/${sessionId}`, { responseType: 'text' })
    ]);

    const session = sessions.value.find(s => s.id === sessionId);
    const parameters = session ? session.parameters : {};
    const endMetrics = endMetricsResponse.data.data;
    const timeSeriesMetrics = Papa.parse(timeSeriesMetricsResponse.data, { header: true }).data;

    // Prepare parameters and end metrics data
    const parameterEntries = Object.entries(parameters);
    const endMetricEntries = Object.entries(endMetrics);
    const maxEntries = Math.max(parameterEntries.length, endMetricEntries.length);

    // Create the combined data
    const combinedData = timeSeriesMetrics.map((row, index) => {
      const newRow = {
        'Parameter': index < parameterEntries.length ? parameterEntries[index][0] : '',
        'Parameter Value': index < parameterEntries.length ? parameterEntries[index][1] : '',
        'End of Run Metric': index < endMetricEntries.length ? endMetricEntries[index][0] : '',
        'End of Run Metric Value': index < endMetricEntries.length ? endMetricEntries[index][1] : '',
        ...row
      };
      return newRow;
    });

    // If time series data has fewer rows than parameters or end metrics, add additional rows
    for (let i = timeSeriesMetrics.length; i < maxEntries; i++) {
      combinedData.push({
        'Parameter': i < parameterEntries.length ? parameterEntries[i][0] : '',
        'Parameter Value': i < parameterEntries.length ? parameterEntries[i][1] : '',
        'End of Run Metric': i < endMetricEntries.length ? endMetricEntries[i][0] : '',
        'End of Run Metric Value': i < endMetricEntries.length ? endMetricEntries[i][1] : '',
      });
    }

    const csv = Papa.unparse(combinedData);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `combined_metrics_${sessionId}.csv`;
    link.click();
  } catch (error) {
    console.error("Error downloading combined CSV:", error);
  }
};

const showResult = async (sessionId) => {
  try {
    const session = sessions.value.find(s => s.id === sessionId);
    if (session) {
      selectedSession.value = session;
      if (!session.endMetrics) {
        const endMetricsResponse = await axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/end_metrics/${sessionId}`);
        session.endMetrics = endMetricsResponse.data.data;
      }
      const plotResponse = await axios.get(`${import.meta.env.VITE_HTTP_URL}experiment/time_series_plot/${sessionId}`, { responseType: 'text' });
      svgPlot.value = plotResponse.data;
      showResultDialog.value = true;
    }
  } catch (error) {
    console.error("Error fetching session results:", error);
  }
};

const closeResultDialog = () => {
  showResultDialog.value = false;
  selectedSession.value = null;
  svgPlot.value = '';
};

onMounted(fetchData);
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  align-items: start;
}

.parameter-card-large {
  grid-column: span 2;
}

.short-input {
  max-width: 100%;
}

.session-plot {
  width: 25%;
  height: 25vh;
  max-width: 300px;
  margin: 0 auto;
}

@media (max-width: 600px) {
  .parameter-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
  .parameter-card-large {
    grid-column: span 1;
  }
}

@media (max-width: 960px) {
  .v-card-title {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .v-card-title .v-btn {
    margin-left: 0 !important;
    margin-top: 8px;
  }
}
</style>