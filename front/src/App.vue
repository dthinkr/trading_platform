<template>
  <v-app>
    <v-main class="fill-height gradient-background">
      <router-view></router-view>
      <!-- This will render the matched component -->
    </v-main>
  </v-app>
</template>

<script setup>
const testValue = import.meta.env.VITE_TEST
</script>

<style>
.gradient-background {
  background: linear-gradient(135deg, #eceff1 0%, #90a4ae 100%);
}

.v-application__wrap {
  min-height: 100vh;
}
</style>
