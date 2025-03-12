<template>
  <v-card elevation="2">
    <v-card-title class="headline">
      <v-icon left color="deep-blue">mdi-account-group-outline</v-icon>
      Prolific Settings
    </v-card-title>
    <v-card-text class="pa-4">
      <v-form>
        <v-textarea
          v-model="settings.credentials"
          label="Prolific Credentials"
          outlined
          dense
          hide-details="auto"
          class="mb-3"
          placeholder="username1,password1
username2,password2
username3,password3"
          hint="Enter one username,password pair per line. No commas in passwords."
          persistent-hint
          rows="5"
        ></v-textarea>
        
        <div class="d-flex align-center mb-3">
          <v-text-field
            v-model="numCredentials"
            label="Number of Credentials"
            type="number"
            min="1"
            max="20"
            outlined
            dense
            hide-details
            class="mr-2"
            style="max-width: 150px;"
          ></v-text-field>
          
          <v-btn
            color="secondary"
            @click="generateCredentials"
            :disabled="generatingCredentials"
            :loading="generatingCredentials"
          >
            <v-icon left>mdi-key-variant</v-icon>
            Generate
          </v-btn>
        </div>
        
        <v-alert
          v-if="credentialsError"
          type="error"
          dense
          class="mb-3"
        >
          {{ credentialsError }}
        </v-alert>
        
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
          :disabled="!!credentialsError"
        >
          <v-icon left>mdi-content-save</v-icon>
          Save Prolific Settings
        </v-btn>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from '@/api/axios';
import { useTraderStore } from "@/store/app";
import Haikunator from 'haikunator';

const traderStore = useTraderStore();
const haikunator = new Haikunator();

const settings = ref({
  credentials: '',
  studyId: '',
  redirectUrl: ''
});
const saving = ref(false);
const numCredentials = ref(5);
const generatingCredentials = ref(false);

// Validate credentials format
const credentialsError = computed(() => {
  if (!settings.value.credentials.trim()) return null;
  
  const lines = settings.value.credentials.trim().split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue; // Skip empty lines
    
    const parts = line.split(',');
    if (parts.length !== 2) {
      return `Line ${i+1}: Each line must contain exactly one username and one password separated by a comma`;
    }
    
    const [username, password] = parts;
    if (!username.trim() || !password.trim()) {
      return `Line ${i+1}: Username and password cannot be empty`;
    }
  }
  
  return null;
});

// Fetch Prolific settings from the server
const fetchSettings = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/prolific-settings`);
    if (response.data && response.data.data) {
      settings.value = {
        credentials: response.data.data.PROLIFIC_CREDENTIALS || '',
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
  // Validate credentials before saving
  if (credentialsError.value) {
    traderStore.showSnackbar({
      text: credentialsError.value,
      color: 'error'
    });
    return;
  }
  
  try {
    saving.value = true;
    
    const settingsData = {
      PROLIFIC_CREDENTIALS: settings.value.credentials,
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

// Generate random username and password pairs
const generateCredentials = () => {
  generatingCredentials.value = true;
  
  try {
    const count = parseInt(numCredentials.value) || 5;
    const generatedCredentials = [];
    
    // Generate the specified number of credential pairs
    for (let i = 0; i < count; i++) {
      // Generate a unique username using haikunator
      const username = haikunator.haikunate({ tokenLength: 0, delimiter: '' });
      
      // Generate a random password (8-12 characters, alphanumeric)
      const passwordLength = Math.floor(Math.random() * 5) + 8; // 8-12 characters
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
      let password = '';
      
      for (let j = 0; j < passwordLength; j++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      
      generatedCredentials.push(`${username},${password}`);
    }
    
    // Update the credentials field
    settings.value.credentials = generatedCredentials.join('\n');
    
    // Show success message
    traderStore.showSnackbar({
      text: `Generated ${count} credential pairs`,
      color: 'success'
    });
  } catch (error) {
    console.error('Error generating credentials:', error);
    
    traderStore.showSnackbar({
      text: 'Failed to generate credentials',
      color: 'error'
    });
  } finally {
    generatingCredentials.value = false;
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
