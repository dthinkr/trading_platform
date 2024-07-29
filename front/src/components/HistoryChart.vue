<template>
  <v-card class="history-chart-container" elevation="3">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-chart-line</v-icon>
      Transaction Price History
    </v-card-title>
    <div class="chart-wrapper">
      <highcharts
        ref="priceGraph"
        :constructor-type="'stockChart'"
        :options="chartOptions"
      >
      </highcharts>
    </div>
  </v-card>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { Chart } from "highcharts-vue";
import HighCharts from "highcharts";
import StockCharts from "highcharts/modules/stock";
import HighchartsNoData from "highcharts/modules/no-data-to-display";

const traderStore = useTraderStore();
const { history } = storeToRefs(traderStore);
const priceGraph = ref(null);

const chartOptions = reactive({
  chart: {
    height: 250,
    backgroundColor: '#f5f5f5',
    style: {
      fontFamily: 'Roboto, sans-serif'
    },
    animation: false
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
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderWidth: 0,
    shadow: true,
    useHTML: true,
    pointFormat: '<span style="color:{point.color}">\u25CF</span> {series.name}: <b>{point.y:.2f}</b><br/>',
    xDateFormat: '%Y-%m-%d %H:%M:%S'
  },
  xAxis: {
    type: "datetime",
    ordinal: false,
    labels: {
      style: {
        color: '#666',
        fontSize: '11px'
      }
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb',
    tickPixelInterval: 150
  },
  yAxis: {
    labels: {
      style: {
        color: '#666',
        fontSize: '11px'
      }
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb',
    tickWidth: 1
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
      lineWidth: 2,
      marker: {
        enabled: true,
        radius: 3,
        symbol: 'circle'
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
      turboThreshold: 0
    },
    line: {
      marker: {
        enabled: true,
        radius: 3,
        symbol: 'circle'
      },
    },
  },
});

watch(
  history,
  (newHistory) => {
    if (newHistory && newHistory.length) {
      const data = newHistory.map((item) => ({
        x: new Date(item.timestamp).getTime(),
        y: item.price,
      }));
      
      if (priceGraph.value && priceGraph.value.chart) {
        priceGraph.value.chart.series[0].setData(data, true, false, false);
      } else {
        chartOptions.series[0].data = data;
      }
    }
  },
  { deep: true }
);

onMounted(async () => {
  await nextTick();
  if (priceGraph.value && priceGraph.value.chart) {
    priceGraph.value.chart.reflow();
  }
});

StockCharts(HighCharts);
HighchartsNoData(HighCharts);
</script>

<script>
export default {
  components: {
    highcharts: Chart,
  },
};
</script>

<style scoped>
.history-chart-container {
  width: 100%;
  background-color: #f5f5f5;
}

.cardtitle-primary {
  color: black;
  font-weight: bold;
  padding: 12px 16px;
}

.chart-wrapper {
  padding: 0 16px 16px;
}

.history-chart-container:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  transition: all 0.3s ease;
}
</style>