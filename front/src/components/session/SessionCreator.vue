<template>
  <v-container fluid class="pa-4">
    <v-row>
      <v-col cols="12" md="8">
        <v-card class="mb-4" elevation="4">
          <v-card-title class="text-h5 font-weight-bold">Trading Session Configuration</v-card-title>
          
          <v-card-text>
            <v-form>
              <div class="parameter-grid">
                <v-card v-for="(group, hint) in groupedFields" :key="hint" outlined class="parameter-card" :class="{ 'parameter-card-large': group.length > 4 }">
                  <v-card-title class="text-subtitle-1 text-capitalize py-2 px-3 grey lighten-4">
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
            >
              <v-icon small left>mdi-content-save</v-icon>
              Save Settings
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card class="mb-4" elevation="4">
          <v-card-title class="text-h5 font-weight-bold">Log Files</v-card-title>
          <v-card-text>
            <v-data-table
              :headers="[
                { text: 'File Name', value: 'name' },
                { text: 'Actions', value: 'actions', sortable: false }
              ]"
              :items="logFiles"
              :items-per-page="5"
              class="elevation-1"
              dense
            >
              <template v-slot:item.actions="{ item }">
                <v-btn x-small text color="primary" @click="viewFile(item.name)">
                  <v-icon small left>mdi-eye</v-icon> View
                </v-btn>
                <v-btn x-small text color="secondary" @click="downloadFile(item.name)">
                  <v-icon small left>mdi-download</v-icon> Download
                </v-btn>
                <v-btn x-small text color="error" @click="confirmDeleteFile(item.name)">
                  <v-icon small left>mdi-delete</v-icon> Delete
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="showFileDialog" @click:outside="closeFileDialog" max-width="600px">
      <v-card v-if="selectedFile">
        <v-card-title class="text-subtitle-1 grey lighten-2">
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

    <!-- Add this dialog for delete confirmation -->
    <v-dialog v-model="showDeleteDialog" max-width="300px">
      <v-card>
        <v-card-title class="text-h5">Confirm Delete</v-card-title>
        <v-card-text>Are you sure you want to delete this file?</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue darken-1" text @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="blue darken-1" text @click="deleteFile">Delete</v-btn>
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
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  align-items: start;
}

.parameter-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.parameter-card-large {
  grid-column: span 2;
}

.short-input {
  max-width: 100%;
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
}

@media (max-width: 960px) {
  .parameter-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
  .parameter-card-large {
    grid-column: span 1;
  }
}
</style>