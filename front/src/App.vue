<template>
  <v-app>
    <v-main class="fill-height gradient-background">
      <router-view></router-view>
      <!-- This will render the matched component -->
    </v-main>
    
    <!-- Global Snackbar for notifications and errors -->
    <v-snackbar
      v-model="uiStore.showSnackbar"
      :color="uiStore.snackbarColor"
      :timeout="uiStore.snackbarTimeout"
      location="top"
      multi-line
    >
      {{ uiStore.snackbarText }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="uiStore.hideMessage()"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { useUIStore } from '@/store/ui'

const uiStore = useUIStore()
</script>

<style>
.gradient-background {
  background: linear-gradient(135deg, #eceff1 0%, #90a4ae 100%);
}

.v-application__wrap {
  min-height: 100vh;
}
</style>
