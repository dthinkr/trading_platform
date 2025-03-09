<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4">
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>
            
            <!-- Loading indicator for Prolific authentication -->
            <div v-if="isProlificUser && isLoading" class="text-center my-6">
              <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
              <p class="text-subtitle-1 mt-4">Authenticating with Prolific...</p>
            </div>
            
            <!-- Regular authentication UI -->
            <template v-else>
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
                <v-btn block color="error" size="x-large" @click="signInWithGoogle" class="mb-4">
                  <v-icon start icon="mdi-google"></v-icon>
                  Sign in with Google
                </v-btn>
                
                <v-btn block color="primary" size="x-large" @click="adminSignInWithGoogle" class="mb-4">
                  <v-icon start icon="mdi-google"></v-icon>
                  Admin Sign in with Google
                </v-btn>
              </template>
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
import { ref, onMounted, defineProps } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { useAuthStore } from '@/store/auth';
import logo from '@/assets/trading_platform_logo.svg';

// Define props that can be passed from the router
const props = defineProps({
  prolificPID: String,
  studyID: String,
  sessionID: String
});

const router = useRouter();
const route = useRoute();
const auth = getAuth();
const authStore = useAuthStore();

const errorMessage = ref('');
const autoSignInBtn = ref(null);
const autoAdminSignInBtn = ref(null);
const isProlificUser = ref(false);
const isLoading = ref(false);

onMounted(async () => {
  // Check for Prolific parameters from both props and URL
  const prolificPID = props.prolificPID || route.query.PROLIFIC_PID;
  const studyID = props.studyID || route.query.STUDY_ID;
  const sessionID = props.sessionID || route.query.SESSION_ID;
  
  console.log('Auth component mounted, checking for Prolific params:', { 
    prolificPID, 
    studyID, 
    sessionID,
    'from props': !!props.prolificPID,
    'from query': !!route.query.PROLIFIC_PID
  });
  
  if (prolificPID && studyID && sessionID) {
    // We have Prolific parameters, handle Prolific login
    isProlificUser.value = true;
    isLoading.value = true;
    
    try {
      console.log('Detected Prolific parameters, attempting login...', {
        PROLIFIC_PID: prolificPID,
        STUDY_ID: studyID,
        SESSION_ID: sessionID
      });
      
      // Delay slightly to ensure components are mounted
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await authStore.prolificLogin({
        PROLIFIC_PID: prolificPID,
        STUDY_ID: studyID,
        SESSION_ID: sessionID
      });
      
      console.log('Prolific login successful:', { 
        traderId: authStore.traderId, 
        marketId: authStore.marketId 
      });
      
      if (authStore.traderId && authStore.marketId) {
        // Redirect to practice page
        const redirectPath = `/onboarding/${authStore.marketId}/${authStore.traderId}/practice`;
        console.log('Redirecting to:', redirectPath);
        
        // Use replace instead of push to avoid navigation issues
        router.replace(redirectPath);
      } else {
        console.error('Missing trader or market ID after Prolific login');
        errorMessage.value = "Login successful but missing trader or market assignment";
      }
    } catch (error) {
      console.error("Prolific login error:", error);
      errorMessage.value = error.message || "An error occurred during Prolific sign-in";
    } finally {
      isLoading.value = false;
    }
  } else {
    // Regular authentication flow
    console.log('No Prolific parameters, using regular authentication');
    await authStore.initializeAuth();
    
    // If user is already authenticated and has trader/market IDs, auto-navigate
    if (authStore.isAuthenticated && authStore.traderId && authStore.marketId) {
      router.push({ 
        name: 'practice',
        params: { 
          traderUuid: authStore.traderId,
          marketId: authStore.marketId
        } 
      });
    }
  }
});

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
