<template>

  <router-view></router-view> <!-- This will render the matched component -->
</template>
<script setup>
const testValue = import.meta.env.VITE_TEST;
</script>