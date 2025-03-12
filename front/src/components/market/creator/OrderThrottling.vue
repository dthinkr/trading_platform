<template>
  <v-card elevation="2">
    <v-card-title class="headline">
      <v-icon left color="deep-blue">mdi-timer-settings-outline</v-icon>
      Order Throttling
    </v-card-title>
    <v-card-text>
      <v-data-table
        :headers="[
          { text: 'Trader Type', value: 'type' },
          { text: 'Throttle (ms)', value: 'throttle' },
          { text: 'Max Orders', value: 'maxOrders' }
        ]"
        :items="traderTypes"
        hide-default-footer
        dense
      >
        <template v-slot:item="{ item }">
          <tr>
            <td>{{ item }}</td>
            <td style="width: 200px">
              <v-text-field
                v-model.number="throttleSettings[item].order_throttle_ms"
                type="number"
                min="0"
                dense
                outlined
                hide-details
                @input="updateSettings"
              ></v-text-field>
            </td>
            <td style="width: 200px">
              <v-text-field
                v-model.number="throttleSettings[item].max_orders_per_window"
                type="number"
                min="1"
                dense
                outlined
                hide-details
                @input="updateSettings"
              ></v-text-field>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, defineProps, defineEmits, computed, watch } from 'vue';

const props = defineProps({
  formState: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:formState']);

const traderTypes = ['HUMAN', 'NOISE', 'INFORMED', 'MARKET_MAKER', 'INITIAL_ORDER_BOOK', 'SIMPLE_ORDER'];

const throttleSettings = computed({
  get: () => props.formState.throttle_settings || {
    HUMAN: { order_throttle_ms: 1000, max_orders_per_window: 2 },
    NOISE: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INFORMED: { order_throttle_ms: 0, max_orders_per_window: 1 },
    MARKET_MAKER: { order_throttle_ms: 0, max_orders_per_window: 1 },
    INITIAL_ORDER_BOOK: { order_throttle_ms: 0, max_orders_per_window: 1 },
    SIMPLE_ORDER: { order_throttle_ms: 0, max_orders_per_window: 1 }
  },
  set: (val) => {
    const newFormState = { ...props.formState, throttle_settings: val };
    emit('update:formState', newFormState);
  }
});

const updateSettings = () => {
  throttleSettings.value = { ...throttleSettings.value };
};
</script>

<style scoped>
.v-data-table :deep(td) {
  padding: 0 7px !important;
}

.v-data-table :deep(.v-data-table__wrapper > table > tbody > tr > td:last-child) {
  width: 1%;
  white-space: nowrap;
}
</style>
