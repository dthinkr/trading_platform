<template>
  <v-card height="100%" elevation="3" class="my-orders-card">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-format-list-bulleted</v-icon>
      My Orders
    </v-card-title>
    
    <div class="table-wrapper">
      <v-data-table
        id="my-orders-table"
        :headers="headers"
        :items="myOrders"
        :items-per-page="-1"
        :fixed-header="true"
        dense
        class="elevation-1"
      >
        <template #item.timestamp="{ item }">
          {{ formatTimestamp(item.timestamp) }}
        </template>
        <template #item.price="{ item }">
          {{ formatNumber(item.price) }}
        </template>
        <template #item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            small
            label
          >
            {{ item.status }}
          </v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            icon
            small
            :disabled="item.status !== 'active'"
            @click="cancelItem(item)"
            :color="item.status === 'active' ? 'error' : ''"
          >
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { useFormatNumber } from '@/composables/utils';

const { formatNumber } = useFormatNumber();
const { myOrders } = storeToRefs(useTraderStore());
const { sendMessage } = useTraderStore();

const headers = [
  { title: "Timestamp", key: "timestamp", align: 'start', sortable: true },
  { title: "Type", key: "order_type", align: 'center', sortable: true },
  { title: "Price", key: "price", align: 'end', sortable: true },
  { title: "Status", key: "status", align: 'center', sortable: true },
  { title: "Actions", key: "actions", align: 'center', sortable: false },
];

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleString(undefined, { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  });
};

const getStatusColor = (status) => {
  switch (status) {
    case 'active': return 'success';
    case 'cancelled': return 'error';
    case 'filled': return 'info';
    default: return 'grey';
  }
};

const cancelItem = (item) => {
  sendMessage("cancel_order", { id: item.id });
};

watch(
  myOrders,
  () => {
    myOrders.value.sort((a, b) => b.timestamp - a.timestamp);
  },
  { immediate: true, deep: true }
);
</script>

<style scoped>
.my-orders-card {
  display: flex;
  flex-direction: column;
}

.cardtitle-primary {
  background-color: var(--v-primary-base);
  color: white;
  font-weight: bold;
  padding: 12px 16px;
}

.table-wrapper {
  flex-grow: 1;
  overflow: auto;
}

#my-orders-table {
  height: 100%;
}

#my-orders-table :deep(.v-data-table__wrapper) {
  height: calc(100% - 48px); /* Adjust for header height */
}

#my-orders-table :deep(.v-data-table__wrapper > table) {
  height: 100%;
}

#my-orders-table :deep(.v-data-table__wrapper th) {
  background-color: var(--v-secondary-lighten5);
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

#my-orders-table :deep(.v-data-table__wrapper td) {
  font-size: 0.875rem;
}

#my-orders-table :deep(.v-data-table__wrapper tr:nth-child(even)) {
  background-color: var(--v-secondary-lighten5);
}

#my-orders-table :deep(.v-data-table__wrapper tr:hover) {
  background-color: var(--v-secondary-lighten4);
}
</style>