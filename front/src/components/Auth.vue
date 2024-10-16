<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card elevation="24" class="auth-card">
          <v-card-text class="text-center">
            <img :src="logo" alt="Trading Logo" class="trading-logo mb-4">
            <h1 class="text-h4 font-weight-bold mb-2">Trade</h1>
            <p class="text-subtitle-1 mb-6">Sign in to access a trading session</p>
            
            <v-btn block color="error" size="x-large" @click="signInWithGoogle" class="mb-4">
              <v-icon start icon="mdi-google"></v-icon>
              Sign in with Google
            </v-btn>
            
            <v-btn block color="primary" size="x-large" @click="adminSignInWithGoogle" class="mb-4">
              <v-icon start icon="mdi-google"></v-icon>
              Admin Sign in with Google
            </v-btn>

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
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { useAuthStore } from '@/store/auth';
import logo from '@/assets/trading_platform_logo.svg';

const router = useRouter();
const auth = getAuth();
const authStore = useAuthStore();

const errorMessage = ref('');

const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    
    await authStore.login(user);
    
    router.push({
      name: 'onboarding',
      params: { 
        traderUuid: authStore.traderId,
        sessionId: authStore.sessionId
      }
    });
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
      router.push('/SessionCreator');
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
