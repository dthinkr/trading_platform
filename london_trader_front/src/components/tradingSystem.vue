<template>
  <v-app class="trading-system">
    <v-app-bar app elevation="2" color="primary" dark>
      <v-container class="py-0 fill-height">
        <v-row align="center" no-gutters>
          <v-col cols="auto">
            <v-card class="mx-3 pa-2" elevation="0" color="primary" dark>
              <template v-if="isTradingStarted">
                <vue-countdown v-if="remainingTime" :time="remainingTime * 1000" v-slot="{ minutes, seconds }">
                  <v-chip color="accent" label class="font-weight-bold">
                    {{ minutes }}:{{ seconds.toString().padStart(2, '0') }}
                  </v-chip>
                </vue-countdown>
              </template>
              <template v-else>
                <v-chip color="warning" label>Waiting to start</v-chip>
              </template>
            </v-card>
          </v-col>
          <v-spacer></v-spacer>
          <v-col cols="auto">
            <v-row no-gutters>
              <v-col v-for="(item, index) in [
                { label: 'VWAP', value: formatNumber(vwap), icon: 'mdi-chart-line' },
                { label: 'PnL', value: pnl, icon: 'mdi-currency-usd' },
                { label: 'Shares', value: `${initial_shares} ${formatDelta}`, icon: 'mdi-file-document-outline' },
                { label: 'Cash', value: cash, icon: 'mdi-cash' }
              ]" :key="index" cols="auto" class="mx-2">
                <v-card outlined class="pa-2" color="primary" dark>
                  <v-row no-gutters align="center">
                    <v-col cols="auto" class="mr-2">
                      <v-icon>{{ item.icon }}</v-icon>
                    </v-col>
                    <v-col>
                      <v-card-subtitle class="pa-0 text-caption white--text">{{ item.label }}</v-card-subtitle>
                      <v-card-text class="pa-0 text-body-1 font-weight-bold white--text">{{ item.value }}</v-card-text>
                    </v-col>
                  </v-row>
                </v-card>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-app-bar>

    <v-main class="grey lighten-4">
      <v-container fluid class="pa-6">
        <v-row>
          <v-col cols="12" lg="6">
            <v-card height="400" class="mb-6" elevation="3">
              <v-card-title class="headline font-weight-bold">
                <v-icon left color="primary">mdi-chart-bell-curve</v-icon>
                Bid-Ask Chart
              </v-card-title>
              <BidAskChart />
            </v-card>
          </v-col>
          <v-col cols="12" lg="6">
            <v-card height="400" class="mb-6" elevation="3">
              <v-card-title class="headline font-weight-bold">
                <v-icon left color="primary">mdi-chart-timeline-variant</v-icon>
                History Chart
              </v-card-title>
              <HistoryChart />
            </v-card>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12" lg="6">
            <myOrdersTable />
          </v-col>
          <v-col cols="12" lg="6">
            <sellingBlock />
          </v-col>
        </v-row>
      </v-container>
    </v-main>

    <v-navigation-drawer app right width="350" permanent class="elevation-4">
      <v-container fluid class="pa-4">
        <messageBlock class="mb-6" />
        <staticInfoBlock />
      </v-container>
    </v-navigation-drawer>

    <v-footer app v-if="goalMessage" :color="goalMessage.type" class="px-4" elevation="3">
      <v-row no-gutters align="center" justify="center">
        <strong class="text-h6">{{ goalMessage.text }}</strong>
      </v-row>
    </v-footer>
  </v-app>
</template>

<script setup>
const props = defineProps({
  traderUuid: String,
});
import commandTool from "@/components/commandToolBar.vue";
import myOrdersTable from "@/components/myOrders.vue";
import BidAskChart from "@/components/BidAskChart.vue";
import HistoryChart from "@/components/HistoryChart.vue";
import sellingBlock from "./sellingBlock.vue";
import messageBlock from "./messageBlock.vue";
import staticInfoBlock from "./staticInfoBlock.vue";
import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useFormatNumber } from "@/composables/utils";

const { formatNumber } = useFormatNumber();
const router = useRouter();
import { storeToRefs } from "pinia";
import { useTraderStore } from "@/store/app";
import { watch } from "vue";
const { initializeTrader } = useTraderStore();
const { gameParams, goalMessage, shares, cash, sum_dinv, initial_shares, dayOver, pnl, vwap, remainingTime, isTradingStarted } =
  storeToRefs(useTraderStore());

// const remainingTime = computed(() => {
//   const currentTime = new Date().getTime();
//   const endTime = new Date(gameParams.value.end_time).getTime();
//   return endTime - currentTime;
// });
onMounted(() => {
  initializeTrader(props.traderUuid);
});
const formatDelta = computed(() => {

  if (sum_dinv == undefined) {
    return "";
  }
  return sum_dinv.value >= 0 ? "+" + sum_dinv.value : sum_dinv.value;
});

const finalizingDay = () => {
  //let's just refresh page
  // location.reload();
  router.push({ name: "DayOver", params: { traderUuid: props.traderUuid } });
};
watch(
  gameParams,
  () => {
    if (gameParams.value.active === false) {
      finalizingDay();
    }
  },
  { immediate: true, deep: true }
);

watch(
  dayOver,
  (newValue) => {
    if (newValue) {
      finalizingDay();
    }
  },
  { immediate: true }
);

watch(
  remainingTime,
  (newValue) => {
    if (newValue !== null && newValue <= 0) {
      finalizingDay();
    }
  }
);
</script>


<style scoped>
.equal-height-columns>.v-col {
  display: flex;
  flex: 1;
}
</style>

<style scoped>
.trading-system {
  font-family: 'Roboto', sans-serif;
}

.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.headline {
  letter-spacing: 0.5px;
}

.v-chip {
  font-weight: 500;
}

.v-navigation-drawer {
  background-color: #f5f5f5;
}

.v-footer {
  transition: all 0.3s ease;
}

.equal-height-columns > .v-col {
  display: flex;
  flex: 1;
}

.flex-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.flex-child {
  flex: 1;
  overflow: auto;
}

@keyframes fadeInHighlight {
  0% {
    background-color: yellow;
    opacity: 0;
  }
  50% {
    background-color: yellow;
    opacity: 0.5;
  }
  100% {
    background-color: transparent;
    opacity: 1;
  }
}

.fade-in-highlight {
  animation: fadeInHighlight 1s ease;
}
</style>