<template>
  <v-container fluid class="pa-4">
    <v-row>
      <v-col cols="12" md="8">
        <v-card class="mb-4" elevation="2">
          <v-card-title class="headline">
            <v-icon left color="deep-blue">mdi-cog-outline</v-icon>
            Trading Session Configuration
          </v-card-title>
          
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
      
      <v-col cols="12" md="4">
        <v-card class="mb-4" elevation="2">
          <v-card-title class="headline">
            <v-icon left color="deep-blue">mdi-file-document-multiple-outline</v-icon>
            Log Files
          </v-card-title>
          <v-card-text>
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
                <v-tooltip bottom>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon x-small color="primary" @click="viewFile(item.name)" v-bind="attrs" v-on="on">
                      <v-icon small>mdi-eye</v-icon>
                    </v-btn>
                  </template>
                  <span>View</span>
                </v-tooltip>
                <v-tooltip bottom>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon x-small color="secondary" @click="downloadFile(item.name)" v-bind="attrs" v-on="on">
                      <v-icon small>mdi-download</v-icon>
                    </v-btn>
                  </template>
                  <span>Download</span>
                </v-tooltip>
                <v-tooltip bottom>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon x-small color="error" @click="confirmDeleteFile(item.name)" v-bind="attrs" v-on="on">
                      <v-icon small>mdi-delete</v-icon>
                    </v-btn>
                  </template>
                  <span>Delete</span>
                </v-tooltip>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="showFileDialog" @click:outside="closeFileDialog" max-width="600px">
      <v-card v-if="selectedFile">
        <v-card-title class="subtitle-1 grey lighten-2">
          <v-icon left color="deep-blue" small>mdi-file-document-outline</v-icon>
          {{ selectedFile }}
          <v-spacer></v-spacer>
          <v-btn icon small @click="closeFileDialog">
            <v-icon small>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="mt-2">
          <pre class="file-content">{{ fileContent }}</pre>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showDeleteDialog" max-width="300px">
      <v-card>
        <v-card-title class="headline">Confirm Delete</v-card-title>
        <v-card-text>Are you sure you want to delete this file?</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue darken-1" text @click="showDeleteDialog = false" class="custom-btn">Cancel</v-btn>
          <v-btn color="blue darken-1" text @click="deleteFile" class="custom-btn">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useTraderStore } from "@/store/app";
import axios from 'axios';

const traderStore = useTraderStore();
const formState = ref({});
const formFields = ref([]);
const serverActive = ref(false);
const logFiles = ref([]);
const selectedFile = ref(null);
const fileContent = ref('');
const showFileDialog = ref(false);
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
  if (value === '') {
    formState.value[fieldName] = [];
  } else {
    formState.value[fieldName] = value.split(',').map(item => item.trim());
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

    for (const [key, value] of Object.entries(defaultData)) {
      formState.value[key] = persistentSettings[key] || value.default;
      formFields.value.push({ name: key, ...value });
    }
    
    logFiles.value = logFilesResponse.data.files;
    serverActive.value = true;
  } catch (error) {
    serverActive.value = false;
    console.error("Failed to fetch data:", error);
  }
};

const updatePersistentSettings = async () => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_persistent_settings`, {
      settings: formState.value
    });
  } catch (error) {
    console.error("Failed to update persistent settings:", error);
    throw error;
  }
};

const saveSettings = async () => {
  try {
    await updatePersistentSettings();
    console.log("Settings saved successfully");
  } catch (error) {
    console.error("Error saving settings:", error);
  }
};

const viewFile = async (fileName) => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${fileName}`);
    selectedFile.value = fileName;
    fileContent.value = response.data;
    showFileDialog.value = true;
  } catch (error) {
    console.error("Error viewing file:", error);
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

const closeFileDialog = () => {
  showFileDialog.value = false;
  selectedFile.value = null;
  fileContent.value = '';
};

onMounted(fetchData);
</script>

<style scoped>
.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
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

.file-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: 'Inter', sans-serif;
}

.headline {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.subtitle-1 {
  font-size: 1.1rem;
  font-weight: 500;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.deep-blue {
  color: #1a237e !important;
}

.custom-btn {
  text-transform: none;
  font-weight: 500;
  letter-spacing: 0.5px;
  font-family: 'Inter', sans-serif;
}

.custom-table {
  font-family: 'Inter', sans-serif;
}

.custom-table >>> .v-data-table__wrapper {
  font-family: 'Inter', sans-serif;
}

.custom-header {
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  color: #2c3e50 !important;
}

@media (max-width: 960px) {
  .parameter-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
  .parameter-card-large {
    grid-column: span 1;
  }
}

.v-data-table >>> td {
  padding: 0 8px !important;
}

.v-data-table >>> .v-data-table__wrapper > table > tbody > tr > td:last-child {
  width: 1%;
  white-space: nowrap;
}

.v-btn.v-btn--icon.v-size--x-small {
  width: 20px;
  height: 20px;
  margin: 0 2px;
}

.v-btn.v-btn--icon.v-size--x-small .v-icon {
  font-size: 16px;
}
</style>