<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4">
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>
            <p class="text-subtitle-1 mb-6">Sign in to access a trading session</p>
            
            <v-btn block color="error" size="x-large" @click="signInWithGoogle" class="mb-6">
              <v-icon start icon="mdi-google"></v-icon>
              Sign in with Google
            </v-btn>
            
            <v-expand-transition>
              <div v-if="showAdminLogin" class="admin-login-form">
                <v-form @submit.prevent="adminLogin">
                  <v-text-field v-model="adminUsername" label="Admin Username" prepend-inner-icon="mdi-account" variant="outlined" class="mb-2"></v-text-field>
                  <v-text-field v-model="adminPassword" label="Admin Password" prepend-inner-icon="mdi-lock" type="password" variant="outlined" class="mb-4"></v-text-field>
                  <v-btn block color="primary" type="submit" size="x-large">Admin Login</v-btn>
                </v-form>
              </div>
            </v-expand-transition>
            
            <v-btn variant="text" @click="showAdminLogin = !showAdminLogin" class="mt-4">
              {{ showAdminLogin ? 'Hide Admin Login' : 'Admin Login' }}
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { useAuthStore } from '@/store/auth';
import logo from '@/assets/trading_platform_logo.svg';

const router = useRouter();
const auth = getAuth();
const authStore = useAuthStore();

const showAdminLogin = ref(false);
const adminUsername = ref('');
const adminPassword = ref('');

const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    console.log("Google sign-in successful", user);
    
    // Use the updated login method
    await authStore.login(user);
    
    // Navigate to OnboardingWizard with sessionId and traderId
    router.push({
      name: 'onboarding',
      params: { 
        traderUuid: authStore.traderId,
        sessionId: authStore.sessionId
      }
    });
  } catch (error) {
    console.error("Google sign-in error:", error);
  }
};

const adminLogin = async () => {
  try {
    console.log('Attempting admin login with:', { username: adminUsername.value, password: adminPassword.value });
    await authStore.adminLogin({
      username: adminUsername.value,
      password: adminPassword.value
    });
    router.push('/SessionCreator');
  } catch (error) {
    console.error("Admin login error:", error);
    // Handle error (show error message to user, etc.)
  }
};
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #eceff1 0%, #90a4ae 100%);
}
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