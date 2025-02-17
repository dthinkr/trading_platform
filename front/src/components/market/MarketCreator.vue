<template>
  <div class="market-creator">
    <v-container fluid class="pa-4">
      <v-row class="mb-4">
        <v-col cols="12">
          <v-card elevation="2">
            <v-card-title class="headline">
              <v-icon left color="deep-blue">mdi-cog-outline</v-icon>
              Trading Market Configuration
            </v-card-title>
            
            <v-card-subtitle class="py-2">
              <v-chip
                small
                outlined
                color="error"
                class="mr-2"
              >
                <v-icon left small color="error">mdi-information-outline</v-icon>
                Highlighted fields in red indicate treatment values that differ from defaults
              </v-chip>
            </v-card-subtitle>
            
            <v-card-text>
              <v-form>
                <div class="parameter-grid">
                  <v-card v-for="(group, hint) in groupedFields" :key="hint" outlined class="parameter-card" :class="{ 'parameter-card-large': group.length > 4 }">
                    <v-card-title class="subtitle-1 py-2 px-3 grey lighten-4">
                      <v-icon left color="deep-blue" small>mdi-label-outline</v-icon>
                      {{ hint.replace('_', ' ') }}
                    </v-card-title>
                    <v-card-text class="pa-3">
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
                            :class="getFieldStyle(field.name)"
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
                            :class="getFieldStyle(field.name)"
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
              <v-spacer></v-spacer>
              <v-btn 
                color="primary" 
                @click="saveSettings" 
                :disabled="!serverActive"
                small
                elevation="2"
                class="custom-btn"
              >
                <v-icon left small>mdi-content-save</v-icon>
                Save Settings
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
        
        <!-- Throttle Settings -->
        <v-col cols="12">
          <v-card elevation="2">
            <v-card-title class="headline">
              <v-icon left color="deep-blue">mdi-timer-settings-outline</v-icon>
              Order Throttling
            </v-card-title>
            <v-card-text>
              <v-data-table
                :headers="[
                  { text: 'Trader Type', value: 'type' },
                  { text: 'Throttle (ms)', value: 'throttle' },
                  { text: 'Max Orders', value: 'maxOrders' }
                ]"
                :items="['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK', 'SIMPLE_ORDER']"
                hide-default-footer
                dense
              >
                <template v-slot:item="{ item }">
                  <tr>
                    <td>{{ item }}</td>
                    <td style="width: 200px">
                      <v-text-field
                        v-model.number="formState.throttle_settings[item].order_throttle_ms"
                        type="number"
                        min="0"
                        dense
                        outlined
                        hide-details
                        @input="updatePersistentSettings"
                      ></v-text-field>
                    </td>
                    <td style="width: 200px">
                      <v-text-field
                        v-model.number="formState.throttle_settings[item].max_orders_per_window"
                        type="number"
                        min="1"
                        dense
                        outlined
                        hide-details
                        @input="updatePersistentSettings"
                      ></v-text-field>
                    </td>
                  </tr>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Market Monitor -->
        <v-col cols="12" md="8">
          <v-card elevation="2">
            <v-card-title class="headline">
              <v-icon left color="deep-blue">mdi-monitor-dashboard</v-icon>
              Active Markets Monitor
            </v-card-title>
            
            <v-card-text>
              <v-data-table
                :headers="[
                  { text: 'Market ID', value: 'market_id', class: 'custom-header' },
                  { text: 'Status', value: 'status', class: 'custom-header' },
                  { text: 'Members', value: 'member_count', class: 'custom-header' },
                  { text: 'Started At', value: 'started_at', class: 'custom-header' }
                ]"
                :items="activeSessions"
                :items-per-page="5"
                class="elevation-1"
                dense
              >
                <template v-slot:item.status="{ item }">
                  <v-chip
                    :color="getStatusColor(item.status)"
                    small
                    label
                  >
                    {{ item.status }}
                  </v-chip>
                </template>
                
                <template v-slot:item.member_count="{ item }">
                  {{ item.member_ids?.length || 0 }}
                </template>
                
                <template v-slot:item.started_at="{ item }">
                  {{ item.started_at ? new Date(item.started_at).toLocaleString() : 'Not started' }}
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card class="mb-4" elevation="2">
            <v-card-title class="headline">
              <v-icon left color="deep-blue">mdi-file-document-multiple-outline</v-icon>
              Log Files
            </v-card-title>
            <v-card-text class="pa-2">
              <v-btn 
                color="primary" 
                @click="downloadAllFiles" 
                block
                elevation="2"
                class="mb-2 custom-btn download-all-btn"
                x-large
              >
                <v-icon left large>mdi-download-multiple</v-icon>
                Download All Files
              </v-btn>

              <v-btn 
                color="secondary" 
                @click="downloadParameterHistory" 
                block
                elevation="2"
                class="mb-2 custom-btn"
                x-large
              >
                <v-icon left large>mdi-history</v-icon>
                Download Parameter History
              </v-btn>
              
              <v-data-table
                :headers="[
                  { text: 'File Name', value: 'name', class: 'custom-header' },
                  { text: 'Actions', value: 'actions', sortable: false, class: 'custom-header' }
                ]"
                :items="logFiles"
                :items-per-page="5"
                class="elevation-1 custom-table"
                dense
              >
                <template v-slot:item.actions="{ item }">
                  <v-btn icon x-small color="primary" @click="downloadFile(item.name)" class="mr-2">
                    <v-icon small>mdi-download</v-icon>
                  </v-btn>
                  <v-btn icon x-small color="error" @click="confirmDeleteFile(item.name)">
                    <v-icon small>mdi-delete</v-icon>
                  </v-btn>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-dialog v-model="showDeleteDialog" max-width="300px">
        <v-card>
          <v-card-title class="headline">Confirm Delete</v-card-title>
          <v-card-text>Are you sure you want to delete this file?</v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="grey darken-1" text @click="showDeleteDialog = false" class="custom-btn">Cancel</v-btn>
            <v-btn color="error" text @click="deleteFile" class="custom-btn">Delete</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useTraderStore } from "@/store/app";
import axios from '@/api/axios';  // Use our custom axios instance instead of the default one
import { saveAs } from 'file-saver';
import JSZip from 'jszip';
import { debounce } from 'lodash';

const traderStore = useTraderStore();

// Market Monitor
const activeSessions = ref([]);

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`);
    activeSessions.value = response.data;
  } catch (error) {
    console.error("Failed to fetch sessions:", error);
  }
};

const getStatusColor = (status) => {
  const colors = {
    'pending': 'warning',
    'active': 'success',
    'completed': 'grey'
  };
  return colors[status] || 'grey';
};

// Set up polling for session updates
let sessionPollingInterval;
const formState = ref({
  throttle_settings: {
    HUMAN: { order_throttle_ms: 1000, max_orders_per_window: 2 },
    NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
    MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
    SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
  }
});
const formFields = ref([]);
const serverActive = ref(false);
const logFiles = ref([]);
const showDeleteDialog = ref(false);
const fileToDelete = ref(null);

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
  if (fieldName === 'predefined_goals') {
    if (value === '') {
      formState.value[fieldName] = [];
    } else if (Array.isArray(value)) {
      formState.value[fieldName] = value.map(v => parseInt(v));
    } else {
      // Convert string input to array of numbers
      formState.value[fieldName] = value.split(',')
        .map(v => parseInt(v.trim()))
        .filter(n => !isNaN(n));
    }
    console.log(`Updated ${fieldName}:`, formState.value[fieldName]); // Debug log
  } else {
    // Handle other array fields
    formState.value[fieldName] = value === '' ? [] : value.split(',').map(item => item.trim());
  }
  updatePersistentSettings();
};

const fetchData = async () => {
  try {
    const [defaultsResponse, persistentSettingsResponse, logFilesResponse] = await Promise.all([
      axios.get(`${import.meta.env.VITE_HTTP_URL}traders/defaults`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}admin/get_persistent_settings`),
      axios.get(`${import.meta.env.VITE_HTTP_URL}files`)
    ]);

    const defaultData = defaultsResponse.data.data;
    const persistentSettings = persistentSettingsResponse.data.data;

    // Initialize formState
    formState.value = {};
    
    // Load the form data first
    for (const [key, value] of Object.entries(defaultData)) {
      if (key !== 'throttle_settings') {
        formState.value[key] = persistentSettings[key] || value.default;
        formFields.value.push({ name: key, ...value });
      }
    }
    
    // Handle throttle settings separately
    const defaultThrottleSettings = {
      HUMAN: { order_throttle_ms: 100, max_orders_per_window: 1 },
      NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
      MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
      INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
      SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
    };
    
    formState.value.throttle_settings = persistentSettings.throttle_settings || defaultThrottleSettings;
    
    logFiles.value = logFilesResponse.data.files;
    serverActive.value = true;
  } catch (error) {
    serverActive.value = false;
    console.error("Failed to fetch data:", error);
  }
};

const debouncedUpdate = debounce(async (settings) => {
  try {
    // Create a clean copy of the settings
    const cleanSettings = { ...settings };
    
    // Ensure throttle settings are properly formatted
    if (cleanSettings.throttle_settings) {
      Object.entries(cleanSettings.throttle_settings).forEach(([trader, config]) => {
        cleanSettings.throttle_settings[trader] = {
          order_throttle_ms: parseInt(config.order_throttle_ms) || 0,
          max_orders_per_window: parseInt(config.max_orders_per_window) || 1
        };
      });
    }
    
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, {
      settings: cleanSettings
    });
  } catch (error) {
    console.error("Failed to update persistent settings:", error);
    throw error;
  }
}, 500);

const updatePersistentSettings = () => {
  debouncedUpdate(formState.value);
};

const saveSettings = async () => {
  try {
    await updatePersistentSettings();
    
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/reset_state`);
    
    console.log("Settings saved and state reset successfully");
  } catch (error) {
    console.error("Error saving settings:", error);
  }
};

const downloadFile = async (fileName) => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${fileName}`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error("Error downloading file:", error);
  }
};

const confirmDeleteFile = (fileName) => {
  fileToDelete.value = fileName;
  showDeleteDialog.value = true;
};

const deleteFile = async () => {
  try {
    await axios.delete(`${import.meta.env.VITE_HTTP_URL}files/${fileToDelete.value}`);
    logFiles.value = logFiles.value.filter(file => file.name !== fileToDelete.value);
    showDeleteDialog.value = false;
    fileToDelete.value = null;
  } catch (error) {
    console.error("Error deleting file:", error);
  }
};

const downloadAllFiles = async () => {
  try {
    const zip = new JSZip();
    
    for (const file of logFiles.value) {
      const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${file.name}`, { responseType: 'blob' });
      zip.file(file.name, response.data);
    }
    
    const content = await zip.generateAsync({ type: "blob" });
    saveAs(content, "all_log_files.zip");
  } catch (error) {
    console.error("Error downloading all files:", error);
  }
};

const downloadParameterHistory = async () => {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_HTTP_URL}admin/download_parameter_history`, 
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'parameter_history.json');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error("Error downloading parameter history:", error);
  }
};

// Add this computed property in the script section after other computed properties:
const getFieldStyle = (fieldName) => {
  const defaultValue = formFields.value.find(f => f.name === fieldName)?.default;
  const currentValue = formState.value[fieldName];
  
  // Check if the values are different, handling different types
  const isDifferent = (() => {
    // Handle array type fields
    if (Array.isArray(defaultValue) || Array.isArray(currentValue)) {
      return JSON.stringify(defaultValue) !== JSON.stringify(currentValue);
    }
    // Handle number type fields
    if (typeof defaultValue === 'number' || typeof currentValue === 'number') {
      return Number(defaultValue) !== Number(currentValue);
    }
    // Handle other types
    return defaultValue !== currentValue;
  })();

  return isDifferent ? 'treatment-value' : '';
};

onMounted(() => {
  fetchData();
  fetchActiveSessions();
  // Poll for session updates every 5 seconds
  sessionPollingInterval = setInterval(fetchActiveSessions, 5000);
});

onUnmounted(() => {
  if (sessionPollingInterval) {
    clearInterval(sessionPollingInterval);
  }
});
</script>

<style scoped>
.market-creator {
  zoom: 90%;
  -moz-transform: scale(0.9);
  -moz-transform-origin: 0 0;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  align-items: start;
}

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.parameter-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.parameter-card-large {
  grid-column: span 2;
}

.short-input {
  max-width: 100%;
  font-family: 'Inter', sans-serif;
}

.headline {
  font-size: 1.35rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.subtitle-1 {
  font-size: 1rem;
  font-weight: 500;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.deep-blue {
  color: #1a237e !important;
}

.custom-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: 0.5px !important;
  font-family: 'Inter', sans-serif !important;
}

.custom-table {
  font-family: 'Inter', sans-serif;
}

.custom-table :deep(.v-data-table__wrapper) {
  font-family: 'Inter', sans-serif;
}

.custom-header {
  font-weight: 600 !important;
  font-size: 0.81rem !important;
  color: #2c3e50 !important;
}

@media (max-width: 960px) {
  .parameter-grid {
    grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));
  }
  .parameter-card-large {
    grid-column: span 1;
  }
}

.v-data-table :deep(td) {
  padding: 0 7px !important;
}

.v-data-table :deep(.v-data-table__wrapper > table > tbody > tr > td:last-child) {
  width: 1%;
  white-space: nowrap;
}

.v-btn.v-btn--icon.v-size--x-small {
  width: 22px;
  height: 22px;
  margin: 0 2px;
}

.v-btn.v-btn--icon.v-size--x-small .v-icon {
  font-size: 14px;
}

.download-all-btn {
  font-size: 1.1rem !important;
  height: 48px !important;
  margin-bottom: 8px !important;
}

.download-all-btn .v-icon {
  font-size: 1.3rem !important;
  margin-right: 8px !important;
}

.v-card-text {
  padding: 8px !important;
}

.v-data-table :deep(.v-data-table__wrapper > table > tbody > tr > td:last-child) {
  width: 1%;
  white-space: nowrap;
}

.v-btn.v-btn--icon.v-size--x-small {
  width: 22px;
  height: 22px;
  margin: 0 2px;
}

.v-btn.v-btn--icon.v-size--x-small .v-icon {
  font-size: 14px;
}

.download-all-btn {
  font-size: 1.2rem !important;
  height: 54px !important;
}

.download-all-btn .v-icon {
  font-size: 1.5rem !important;
}

.v-chip {
  font-family: 'Inter', sans-serif !important;
}

.treatment-changes {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 8px;
}

.treatments-container {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 8px;
}

.treatment-card {
  flex: 0 0 300px;
  transition: all 0.3s ease;
  cursor: pointer;
  border: 2px solid transparent;
}

.treatment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.treatment-card-active {
  border-color: var(--v-primary-base);
  background-color: rgba(var(--v-primary-base), 0.05);
}

.treatment-title {
  font-size: 1rem;
  padding: 12px;
}

.treatment-changes {
  padding: 8px 12px;
}

.change-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-size: 0.9rem;
}

.change-field {
  font-weight: 500;
  color: #666;
}

.change-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.old-value {
  color: #999;
  text-decoration: line-through;
}

.new-value {
  color: var(--v-primary-base);
  font-weight: 500;
}

.treatment-timestamp {
  font-size: 0.8rem;
  color: #999;
  padding: 8px 12px;
  border-top: 1px solid #eee;
}

.treatment-value {
  background-color: rgba(244, 67, 54, 0.05) !important; /* Light red background */
}

.treatment-value :deep(.v-input__slot) {
  border: 2px solid #f44336 !important; /* Red border */
}

.treatment-value :deep(.v-label) {
  color: #f44336 !important; /* Red label */
  font-weight: 600;
}

.treatment-value :deep(input) {
  color: #f44336 !important; /* Red text */
  font-weight: 600;
}
</style>


