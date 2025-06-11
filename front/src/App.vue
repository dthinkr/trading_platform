<template>
  <div id="app" class="min-h-screen bg-neutral-50">
    <!-- Skip to content link for accessibility -->
    <a href="#main-content" class="skip-link">
      Skip to main content
    </a>
    
    <!-- Main application -->
    <main id="main-content" class="min-h-screen">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
// The app is now purely declarative with minimal setup
// All logic is handled in individual components and stores
</script>

<style scoped>
/* Component-specific styles if needed */
</style>