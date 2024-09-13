<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4" class="d-flex flex-column align-center">
        <v-card elevation="12" class="auth-card pa-8" width="100%">
          <v-card-title class="text-h4 font-weight-bold text-center mb-4">
            Welcome
            <img :src="logo" alt="Trading Logo" class="trading-logo">
          </v-card-title>
          <v-card-subtitle class="text-center mb-6">
            Sign in to access the trading session
          </v-card-subtitle>
          <v-card-text>
            <v-btn
              block
              color="error"
              size="large"
              @click="signInWithGoogle"
              class="mb-4"
            >
              Sign in with Google
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import logo from '@/assets/trading_platform_logo.png';

const router = useRouter();
const auth = getAuth();

const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    console.log("Google sign-in successful", result.user);
    router.push('/trading/CreateTradingSession');
  } catch (error) {
    console.error("Google sign-in error:", error);
    console.error("Error code:", error.code);
    console.error("Error message:", error.message);
    if (error.customData) {
      console.error("Custom data:", error.customData);
    }
  }
};
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  background: linear-gradient(to right, #4a00e0, #8e2de2);
}
.auth-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  max-width: 400px;
  width: 100%;
}
.trading-logo {
  width: 20px;
  height: 50px;
  vertical-align: middle;
  margin-left: 8px;
}
</style>