<template>
  <v-card class="history-chart-container" elevation="3">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-chart-line</v-icon>
      Transaction Price History
    </v-card-title>
    <div class="chart-wrapper">
      <highcharts-chart
        :constructor-type="'stockChart'"
        :options="chartOptions"
        :deepCopyOnUpdate="true"
      >
      </highcharts-chart>
    </div>
  </v-card>
</template>

<script setup>
import { ref, reactive, onMounted, watch, watchEffect } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { Chart } from "highcharts-vue";
import Highcharts from "highcharts";
import StockCharts from "highcharts/modules/stock";
import HighchartsNoData from "highcharts/modules/no-data-to-display";

StockCharts(Highcharts);
HighchartsNoData(Highcharts);

const traderStore = useTraderStore();
const { history } = storeToRefs(traderStore);

const chartOptions = reactive({
  chart: {
    height: 250,
    backgroundColor: '#FFFFFF',
    style: {
      fontFamily: 'Roboto, sans-serif'
    },
    animation: false,
    marginTop: 0,
    marginBottom: 0
  },
  navigator: {
    enabled: false,
  },
  credits: {
    enabled: false,
  },
  rangeSelector: {
    enabled: false,
  },
  tooltip: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E0E0E0',
    borderWidth: 1,
    shadow: false,
    useHTML: true,
    style: {
      fontSize: '14px'
    },
    pointFormat: '<span style="color:{point.color}">\u25CF</span> {series.name}: <b>${point.y:.2f}</b><br/>',
    xDateFormat: '%Y-%m-%d %H:%M:%S'
  },
  xAxis: {
    type: "datetime",
    ordinal: false,
    labels: {
      style: {
        color: '#333333',
        fontSize: '12px'
      }
    },
    lineWidth: 0,
    tickWidth: 0,
    tickPixelInterval: 150
  },
  yAxis: {
    gridLineWidth: 0,
    labels: {
      style: {
        color: '#333333',
        fontSize: '12px'
      },
      formatter: function() {
        return '$' + Math.round(this.value);
      },
      align: 'right',
      x: -8,
      y: 3
    },
    lineWidth: 1,
    tickWidth: 1,
    tickLength: 6,
    tickPosition: 'outside',
    opposite: true,
    title: {
      text: null
    },
    allowDecimals: false,
    startOnTick: true,
    endOnTick: true
  },
  title: { 
    text: null
  },
  time: {
    useUTC: false,
  },
  series: [
    {
      name: "Price",
      data: [],
      color: '#2196F3',
      lineWidth: 1.5,
      marker: {
        enabled: false,
        states: {
          hover: {
            enabled: true,
            radius: 3
          }
        }
      },
      animation: false
    },
  ],
  lang: {
    noData: "No transaction data available",
  },
  noData: {
    style: {
      fontWeight: "bold",
      fontSize: "16px",
      color: "#888",
    },
  },
  plotOptions: {
    series: {
      animation: false,
      turboThreshold: 0,
      states: {
        hover: {
          enabled: true,
          lineWidth: 2
        }
      }
    },
  },
});

watchEffect(() => {
  console.log('watchEffect triggered. Current history:', history.value);
  console.log('Current transaction price:', traderStore.transaction_price);
  
  if (history.value && history.value.length) {
    const data = history.value.map((item) => [
      new Date(item.timestamp).getTime(),
      item.price,
    ]);
    
    chartOptions.series[0].data = data;
  } else if (traderStore.transaction_price !== null) {
    // Fallback: Use the most recent transaction price
    const currentTime = new Date().getTime();
    const data = [[currentTime, traderStore.transaction_price]];
    
    console.log('Using fallback data:', data);
    
    chartOptions.series[0].data = data;
  } else {
    console.log('No history data and no transaction price available');
  }
});

// Remove the watch function and onMounted hook
</script>

<script>
export default {
  components: {
    highchartsChart: Chart,
  },
};
</script>

<style scoped>
.history-chart-container {
  width: 100%;
  background-color: #FFFFFF;
  overflow: hidden;
}

.cardtitle-primary {
  color: black;
  font-weight: bold;
  padding: 12px 16px;
  border-bottom: none;
}

.chart-wrapper {
  padding: 0;
}

.history-chart-container:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  transition: all 0.3s ease;
}

:deep(.highcharts-container) {
  border-top: none !important;
}
</style>