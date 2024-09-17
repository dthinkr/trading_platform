<template>
  <v-app>
    <v-main class="day-over-background">
      <v-container class="d-flex align-center justify-center" style="height: 100%;">
        <v-card class="day-over-card" elevation="8" max-width="600px" width="100%">
          <v-card-title class="text-h4 font-weight-bold text-center py-4 primary white--text">
            Session Overview
          </v-card-title>
          <v-card-text class="pa-6">
            <v-list>
              <v-list-item v-for="(item, index) in overviewItems" :key="index" class="mb-4">
                <v-list-item-content>
                  <v-list-item-title class="text-subtitle-1 font-weight-medium">{{ item.title }}</v-list-item-title>
                  <v-list-item-subtitle class="text-h6 mt-1" :class="item.valueClass">
                    {{ formatValue(traderInfo?.[item.key], item.format) }}
                  </v-list-item-subtitle>
                </v-list-item-content>
                <v-list-item-action>
                  <v-icon :color="item.iconColor" large>{{ item.icon }}</v-icon>
                </v-list-item-action>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions class="justify-center pa-4">
            <v-btn color="primary" large @click="goToRegister" class="mr-2">
              Return to Register
            </v-btn>
            <v-btn color="secondary" large @click="downloadSessionMetrics">
              Download Session Metrics
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import axios from "axios";
import { useRouter } from 'vue-router';

const props = defineProps({
  traderUuid: String,
});

const router = useRouter();
const traderInfo = ref(null);
const httpUrl = import.meta.env.VITE_HTTP_URL;

const overviewItems = computed(() => [
  { title: 'Initial Cash', key: 'initial_cash', icon: 'mdi-cash-multiple', iconColor: 'green', format: 'currency' },
  { title: 'Final Cash', key: 'cash', icon: 'mdi-cash', iconColor: 'blue', format: 'currency' },
  { title: 'Change in Cash', key: 'delta_cash', icon: 'mdi-cash-plus', iconColor: 'orange', valueClass: 'font-weight-bold', format: 'currency' },
  { title: 'Initial Shares', key: 'initial_shares', icon: 'mdi-chart-timeline-variant', iconColor: 'purple', format: 'number' },
  { title: 'Final Shares', key: 'shares', icon: 'mdi-chart-bar', iconColor: 'indigo', format: 'number' },
  { title: 'Total Orders Placed', key: 'placed_orders', icon: 'mdi-clipboard-list', iconColor: 'teal', format: 'number' },
  { title: 'Total Orders Filled', key: 'filled_orders', icon: 'mdi-clipboard-check', iconColor: 'light-green', format: 'number' },
  { title: 'Goal Achieved', key: 'goal', icon: 'mdi-flag-checkered', iconColor: 'red', format: 'boolean' },
]);

async function fetchTraderInfo() {
  try {
    const response = await axios.get(`${httpUrl}trader_info/${props.traderUuid}`);
    traderInfo.value = response.data.data;
  } catch (error) {
    console.error('Failed to fetch trader info:', error);
  }
}

const formatValue = (value, format) => {
  if (format === 'currency' && typeof value === 'number') {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  } else if (format === 'number' && typeof value === 'number') {
    return value.toLocaleString('en-US');
  } else if (format === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  return value;
};

const goToRegister = () => {
  router.push({ name: 'Register' });
};

const downloadSessionMetrics = async () => {
  try {
    const response = await axios.get(`${httpUrl}session_metrics/trader/${props.traderUuid}`, {
      responseType: 'blob',
    });
    
    const blob = new Blob([response.data], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = `session_metrics_${props.traderUuid}.csv`;
    link.click();
    
    window.URL.revokeObjectURL(link.href);
  } catch (error) {
    console.error('Failed to download session metrics:', error);
  }
};

onMounted(fetchTraderInfo);
</script>

<style scoped>
.day-over-background {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.day-over-card {
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.day-over-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 20px rgba(0, 0, 0, 0.1);
}

.v-list-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.v-list-item:last-child {
  border-bottom: none;
}
</style>