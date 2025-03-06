<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4">
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>
            <p class="text-subtitle-1 mb-6">Sign in to access a trading market</p>
            
            <!-- Hidden buttons that will be auto-clicked -->
            <v-btn
              ref="autoSignInBtn"
              v-show="false"
              @click="signInWithGoogle"
            ></v-btn>
            
            <v-btn
              ref="autoAdminSignInBtn"
              v-show="false"
              @click="adminSignInWithGoogle"
            ></v-btn>

            <!-- Visible buttons for manual login -->
            <template v-if="!authStore.isAuthenticated">
              <v-form @submit.prevent="signInWithProlific" class="mb-4">
                <v-text-field
                  v-model="prolificId"
                  label="Prolific ID"
                  variant="outlined"
                  placeholder="Enter your Prolific ID"
                  :rules="[v => !!v || 'Prolific ID is required']"
                  required
                ></v-text-field>
                
                <v-btn block color="primary" size="x-large" type="submit" class="mb-4">
                  <v-icon start icon="mdi-login"></v-icon>
                  Sign in with Prolific ID
                </v-btn>
              </v-form>
              
              <v-btn block color="error" size="x-large" @click="signInWithGoogle" class="mb-4">
                <v-icon start icon="mdi-google"></v-icon>
                Sign in with Google
              </v-btn>
              
              <v-btn block color="secondary" size="x-large" @click="adminSignInWithGoogle" class="mb-4">
                <v-icon start icon="mdi-google"></v-icon>
                Admin Sign in
              </v-btn>
            </template>

            <v-alert
              v-if="errorMessage"
              type="error"
              class="mt-4"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { useAuthStore } from '@/store/auth';
import logo from '@/assets/trading_platform_logo.svg';

const router = useRouter();
const auth = getAuth();
const authStore = useAuthStore();

const errorMessage = ref('');
const prolificId = ref('');
const autoSignInBtn = ref(null);
const autoAdminSignInBtn = ref(null);

onMounted(async () => {
  // Wait for auth initialization
  await authStore.initializeAuth();
  
  // Check for Prolific ID in URL params (if redirected from Prolific)
  const urlParams = new URLSearchParams(window.location.search);
  const prolificIdFromUrl = urlParams.get('PROLIFIC_PID');
  
  if (prolificIdFromUrl) {
    prolificId.value = prolificIdFromUrl;
    // Auto sign in if ID is found in URL
    await signInWithProlific();
  } else if (authStore.isAuthenticated && authStore.traderId && authStore.marketId) {
    // If user is already authenticated and has trader/market IDs, auto-navigate
    router.push({ 
      name: 'practice',
      params: { 
        traderUuid: authStore.traderId,
        marketId: authStore.marketId
      } 
    });
  }
});

const signInWithProlific = async () => {
  if (!prolificId.value) {
    errorMessage.value = 'Please enter your Prolific ID';
    return;
  }
  
  try {
    await authStore.loginWithProlific(prolificId.value);
    
    if (authStore.traderId && authStore.marketId) {
      // Check if this is a persisted login
      if (authStore.isPersisted) {
        router.push({ 
          name: 'practice',  // Go directly to practice page
          params: { 
            traderUuid: authStore.traderId,
            marketId: authStore.marketId
          } 
        });
      } else {
        router.push({ 
          name: 'welcome',  // New users start from welcome page
          params: { 
            traderUuid: authStore.traderId,
            marketId: authStore.marketId
          } 
        });
      }
    }
  } catch (error) {
    console.error("Prolific sign-in error:", error);
    errorMessage.value = error.message || "An error occurred during sign-in";
  }
};

// Keep original Google sign-in for backwards compatibility
const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    
    await authStore.login(user);
    
    if (authStore.traderId && authStore.marketId) {
      // Check if this is a persisted login
      if (authStore.isPersisted) {
        router.push({ 
          name: 'practice',  // Go directly to practice page
          params: { 
            traderUuid: authStore.traderId,
            marketId: authStore.marketId
          } 
        });
      } else {
        router.push({ 
          name: 'welcome',  // New users start from welcome page
          params: { 
            traderUuid: authStore.traderId,
            marketId: authStore.marketId
          } 
        });
      }
    }
  } catch (error) {
    console.error("Google sign-in error:", error);
    errorMessage.value = error.message || "An error occurred during sign-in";
  }
};

// Keep Google admin login for admins
const adminSignInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    
    await authStore.adminLogin(user);
    
    if (authStore.isAdmin) {
      router.push('/MarketCreator');
    } else {
      errorMessage.value = "You do not have admin privileges.";
    }
  } catch (error) {
    console.error("Admin Google sign-in error:", error);
    errorMessage.value = error.message || "An error occurred during admin sign-in";
  }
};
</script>

<style scoped>

.auth-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  max-width: 400px;
  width: 100%;
}
.trading-logo {
  width: 80%;
  height: 80%;
  vertical-align: middle;
  margin-left: 8px;
}

.admin-login-form {
  width: 100%;
}
</style>
