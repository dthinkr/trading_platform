<template>
  <v-card elevation="2">
    <v-card-title class="headline">
      <v-icon left color="deep-blue">mdi-account-group-outline</v-icon>
      Prolific Settings
    </v-card-title>
    <v-card-text class="pa-4">
      <v-form>
        <v-text-field
          v-model="settings.apiKey"
          label="Prolific API Key"
          outlined
          dense
          hide-details="auto"
          class="mb-3"
          :append-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
          :type="showApiKey ? 'text' : 'password'"
          @click:append="showApiKey = !showApiKey"
        ></v-text-field>
        
        <v-text-field
          v-model="settings.studyId"
          label="Prolific Study ID"
          outlined
          dense
          hide-details="auto"
          class="mb-3"
        ></v-text-field>
        
        <v-text-field
          v-model="settings.redirectUrl"
          label="Prolific Redirect URL"
          outlined
          dense
          hide-details="auto"
          class="mb-3"
        ></v-text-field>
        
        <v-btn
          color="primary"
          block
          @click="saveSettings"
          class="mt-3"
          :loading="saving"
        >
          <v-icon left>mdi-content-save</v-icon>
          Save Prolific Settings
        </v-btn>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '@/api/axios';
import { useTraderStore } from "@/store/app";

const traderStore = useTraderStore();

const settings = ref({
  apiKey: '',
  studyId: '',
  redirectUrl: ''
});
const showApiKey = ref(false);
const saving = ref(false);

// Fetch Prolific settings from the server
const fetchSettings = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`);
    if (response.data && response.data.data) {
      settings.value = {
        apiKey: response.data.data.PROLIFIC_API || '',
        studyId: response.data.data.PROLIFIC_STUDY_ID || '',
        redirectUrl: response.data.data.PROLIFIC_REDIRECT_URL || ''
      };
    }
  } catch (error) {
    console.error("Failed to fetch Prolific settings:", error);
  }
};

// Save Prolific settings to the server
const saveSettings = async () => {
  try {
    saving.value = true;
    
    const settingsData = {
      PROLIFIC_API: settings.value.apiKey,
      PROLIFIC_STUDY_ID: settings.value.studyId,
      PROLIFIC_REDIRECT_URL: settings.value.redirectUrl
    };
    
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`, { settings: settingsData });
    
    // Show success message
    traderStore.showSnackbar({
      text: 'Prolific settings saved successfully',
      color: 'success'
    });
  } catch (error) {
    console.error("Failed to save Prolific settings:", error);
    
    // Show error message
    traderStore.showSnackbar({
      text: 'Failed to save Prolific settings',
      color: 'error'
    });
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  fetchSettings();
});
</script>

<style scoped>
.headline {
  font-size: 1.35rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
}

.deep-blue {
  color: #1a237e !important;
}
</style>
