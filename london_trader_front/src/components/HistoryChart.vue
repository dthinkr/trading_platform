<template>
  <div class="history-chart-container">
    <highcharts
      ref="priceGraph"
      :constructor-type="'stockChart'"
      :options="chartOptions"
    >
    </highcharts>
  </div>
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
    height: 300,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    style: {
      fontFamily: 'Roboto, sans-serif'
    },
    animation: false // Disable animations for faster rendering
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
    backgroundColor: 'rgba(247, 247, 247, 0.95)',
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
        fontSize: '12px'
      }
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb',
    tickPixelInterval: 150 // Adjust this value to control the density of x-axis ticks
  },
  yAxis: {
    labels: {
      style: {
        color: '#666',
        fontSize: '12px'
      }
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb',
    tickWidth: 1
  },
  title: { 
    text: "Transaction Price History",
    style: {
      color: '#333',
      fontWeight: 'bold'
    }
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
      animation: false // Disable animations for the series
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
      animation: false, // Disable animations for all series
      turboThreshold: 0 // Disable turbo threshold to always use the marker
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
      
      // Update the series data
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
  height: 300px;
  background: linear-gradient(to bottom, #f8f9fa, #ffffff);
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 16px;
  transition: all 0.3s ease;
}

.history-chart-container:hover {
  box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}
</style>