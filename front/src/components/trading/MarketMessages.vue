<template>
  <v-card height="100%" elevation="3" class="market-info-card">
    <v-card-text class="market-info-content" ref="messageContainer">
      <v-list>
        <v-list-item v-for="(item, index) in extraParams" :key="item.var_name" class="market-info-item">
          <v-list-item-title class="info-title">
            {{ item.display_name }}
            <v-tooltip location="bottom" :text="item.explanation" max-width="300">
              <template v-slot:activator="{ props }">
                <v-icon x-small v-bind="props" color="grey lighten-1">mdi-information-outline</v-icon>
              </template>
            </v-tooltip>
          </v-list-item-title>
          <v-list-item-subtitle class="info-value" :class="[getValueColor(item.value), item.var_name === 'noise_trader_status' ? 'status-' + item.value : '']">
            {{ formatValue(item.value) }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";

const { extraParams } = storeToRefs(useTraderStore());

const formatValue = (value) => {
  if (typeof value === 'number') {
    return value.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
  }
  return value;
};

const getValueColor = (value) => {
  if (typeof value === 'number') {
    return value > 0 ? 'green--text' : value < 0 ? 'red--text' : '';
  }
  if (value === 'sleeping') {
    return 'orange--text';
  }
  if (value === 'active') {
    return 'green--text';
  }
  return '';
};

onMounted(() => {
  // Any necessary setup
});
</script>

<style scoped>
.market-info-card {
  background-color: #FFFFFF;
  font-family: 'Inter', sans-serif;
}

.market-info-content {
  height: 300px;
  overflow-y: auto;
  padding: 0;
}

.info-title {
  font-size: 12px;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
}

.v-icon.v-icon--size-x-small {
  font-size: 14px;
  margin-left: 4px;
}

/* Custom scrollbar for webkit browsers */
.market-info-content::-webkit-scrollbar {
  width: 8px;
}

.market-info-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.market-info-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.market-info-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.status-sleeping {
  font-weight: bold;
  background-color: rgba(255, 152, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.status-active {
  font-weight: bold;
  background-color: rgba(76, 175, 80, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}
</style>