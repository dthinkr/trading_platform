<template>
  <v-container fluid class="auth-wrapper fill-height">
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4" class="d-flex flex-column align-center">
        <v-card elevation="12" class="auth-card pa-8" width="100%">
          <v-card-title class="text-h4 font-weight-bold text-center mb-4">
            {{ isLogin ? 'Welcome back' : 'Join' }}
            <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="44.352pt" height="110.88pt" viewBox="0 0 44.352 110.88" version="1.1" class="trading-logo">
              <g id="axes_1">
                <g id="patch_2">
                  <path d="M 2.016 94.64 L 8.736 94.64 L 8.736 72.24 L 2.016 72.24 z" style="fill: #ffffff; stroke: #000000; stroke-linejoin: miter"/>
                </g>
                <g id="patch_3">
                  <path d="M 13.216 72.24 L 19.936 72.24 L 19.936 38.64 L 13.216 38.64 z" style="fill: #ffffff; stroke: #000000; stroke-linejoin: miter"/>
                </g>
                <g id="patch_4">
                  <path d="M 24.416 38.64 L 31.136 38.64 L 31.136 49.84 L 24.416 49.84 z" style="stroke: #000000; stroke-linejoin: miter"/>
                </g>
                <g id="patch_5">
                  <path d="M 35.616 49.84 L 42.336 49.84 L 42.336 27.44 L 35.616 27.44 z" style="fill: #ffffff; stroke: #000000; stroke-linejoin: miter"/>
                </g>
                <g id="line2d_1">
                  <path d="M 5.376 105.84 L 5.376 61.04" style="fill: none; stroke: #000000; stroke-width: 1.5; stroke-linecap: square"/>
                </g>
                <g id="line2d_2">
                  <path d="M 16.576 83.44 L 16.576 27.44" style="fill: none; stroke: #000000; stroke-width: 1.5; stroke-linecap: square"/>
                </g>
                <g id="line2d_3">
                  <path d="M 27.776 61.04 L 27.776 5.04" style="fill: none; stroke: #000000; stroke-width: 1.5; stroke-linecap: square"/>
                </g>
                <g id="line2d_4">
                  <path d="M 38.976 61.04 L 38.976 16.24" style="fill: none; stroke: #000000; stroke-width: 1.5; stroke-linecap: square"/>
                </g>
              </g>
            </svg>
          </v-card-title>
          <v-card-subtitle class="text-center mb-6">
            {{ isLogin ? 'Access your account' : 'Register for the experimental trading session' }}
          </v-card-subtitle>
          <v-card-text>
            <v-form @submit.prevent="submitForm">
              <v-text-field
                v-model="username"
                :rules="[v => !!v || 'Username is required']"
                label="Username"
                placeholder="johndoe"
                prepend-inner-icon="mdi-account"
                required
                class="mb-4"
              />
              <v-text-field
                v-model="password"
                :rules="[v => !!v || 'Password is required']"
                :type="showPassword ? 'text' : 'password'"
                label="Password"
                placeholder="············"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
                required
                class="mb-4"
              />
              <div v-if="isLogin" class="d-flex justify-space-between align-center mb-4">
                <v-checkbox label="Remember me" hide-details />
                <a href="#" class="text-primary text-decoration-none">Forgot Password?</a>
              </div>
              <v-btn
                block
                color="primary"
                size="large"
                type="submit"
                :loading="loading"
                class="mb-4"
              >
                {{ isLogin ? 'Login' : 'Sign up' }}
              </v-btn>
              <div class="text-center">
                <span>{{ isLogin ? "New on our platform?" : "Already have an account?" }}</span>
                <a
                  href="#"
                  class="text-primary text-decoration-none ml-2"
                  @click.prevent="toggleForm"
                >
                  {{ isLogin ? 'Create an account' : 'Sign in instead' }}
                </a>
              </div>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useTraderStore } from '@/store/app';

export default {
  setup() {
    const router = useRouter();
    const traderStore = useTraderStore();
    const username = ref('');
    const password = ref('');
    const showPassword = ref(false);
    const loading = ref(false);
    const isLogin = ref(true);

    const submitForm = async () => {
      loading.value = true;
      try {
        if (isLogin.value) {
          const isAdmin = await traderStore.login(username.value, password.value);
          if (isAdmin) {
            router.push({ name: 'CreateTradingSession' });
          } else {
            router.push({ name: 'LandingPage' });
          }
        } else {
          await traderStore.register(username.value, password.value);
          router.push({ name: 'LandingPage' });
        }
      } catch (error) {
        console.error(isLogin.value ? 'Login failed:' : 'Registration failed:', error);
        // Handle error (show error message to user)
      } finally {
        loading.value = false;
      }
    };

    const toggleForm = () => {
      isLogin.value = !isLogin.value;
      username.value = '';
      password.value = '';
    };

    return {
      username,
      password,
      showPassword,
      loading,
      isLogin,
      submitForm,
      toggleForm,
    };
  },
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