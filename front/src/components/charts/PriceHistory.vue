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
      fontSize: '24px'
    },
    formatter: function() {
      return `<div style="padding: 8px;">
        <div>Price: <b>$${Math.round(this.y)}</b></div>
      </div>`;
    },
    followPointer: true,
    hideDelay: 200,
    outside: true,
    useUTC: false
  },
  xAxis: {
    type: "datetime",
    ordinal: false,
    labels: {
      style: {
        color: '#666',
        fontSize: '12px'
      },
      format: '{value:%H:%M:%S}',
      useUTC: false
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
    opposite: false,
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
    timezone: 'local'
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
      dataLabels: {
        enabled: false
      },
      animation: false
    },
  ],
  noData: {
    position: {
      align: 'center',
      verticalAlign: 'middle'
    },
    style: {
      fontWeight: "bold",
      fontSize: "14px",
      color: "#888",
    },
    attr: {
      'stroke-width': 1,
      stroke: '#cccccc'
    }
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
      const data = newHistory.map((item) => {
        const timestamp = new Date(item.timestamp).getTime();
        const price = Math.round(item.price);
        return {
          x: timestamp,
          y: price
        };
      });
      
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