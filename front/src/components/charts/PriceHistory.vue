<template>
  <v-card class="history-chart-container" elevation="3">
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
import { ref, reactive, onMounted, watch, nextTick, computed } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { Chart } from "highcharts-vue";
import HighCharts from "highcharts";
import StockCharts from "highcharts/modules/stock";
import HighchartsNoData from "highcharts/modules/no-data-to-display";

const traderStore = useTraderStore();
const { history, gameParams } = storeToRefs(traderStore);
const priceGraph = ref(null);

const step = computed(() => gameParams.value.step || 1);
const initialMidPrice = computed(() => gameParams.value.initial_mid_price || 100);

const chartOptions = reactive({
  chart: {
    height: 250,
    backgroundColor: '#FFFFFF',
    style: {
      fontFamily: 'Inter, sans-serif'
    },
    animation: false,
    marginTop: 10,
    marginBottom: 30
  },
  navigator: {
    enabled: false,
  },
  scrollbar: {
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
      fontSize: '12px'
    },
    pointFormat: '<span style="color:{point.color}">\u25CF</span> {series.name}: <b>${point.y:.2f}</b><br/>',
    xDateFormat: '%Y-%m-%d %H:%M:%S'
  },
  xAxis: {
    type: "datetime",
    ordinal: false,
    labels: {
      style: {
        color: '#666',
        fontSize: '10px'
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
        color: '#666',
        fontSize: '10px'
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
      lineWidth: 3,
      marker: {
        enabled: true,
        radius: 4,
        symbol: 'circle',
        fillColor: '#2196F3',
        states: {
          hover: {
            enabled: true,
            radiusPlus: 2
          }
        }
      },
      animation: false
    },
  ],
  noData: {
    style: {
      fontWeight: "bold",
      fontSize: "14px",
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
          lineWidth: 4
        }
      }
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
  background-color: #FFFFFF;
  overflow: hidden;
  font-family: 'Inter', sans-serif;
}

.chart-wrapper {
  padding: 0;
}

:deep(.highcharts-container) {
  font-family: 'Inter', sans-serif !important;
}

:deep(.highcharts-axis-labels),
:deep(.highcharts-axis-title) {
  font-size: 10px !important;
  font-weight: 400 !important;
}

:deep(.highcharts-tooltip) {
  font-size: 12px !important;
}
</style>