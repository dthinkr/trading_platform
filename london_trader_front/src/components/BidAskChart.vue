<template>
  <div class="bid-ask-chart-container">
    <highcharts-chart
      :constructor-type="'chart'"
      :options="chartOptions"
      :deepCopyOnUpdate="true"
    ></highcharts-chart>
  </div>
</template>

<script setup>
import { reactive, watchEffect, ref } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { Chart as HighchartsChart } from "highcharts-vue";
import Highcharts from 'highcharts';
import AnnotationsModule from 'highcharts/modules/annotations';

AnnotationsModule(Highcharts);

const { chartData, midPoint } = storeToRefs(useTraderStore());
import { watch } from "vue";

const chartOptions = reactive({
  chart: {
    type: "column",
    animation: false,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    style: {
      fontFamily: 'Roboto, Arial, sans-serif'
    },
    height: 300
  },
  title: {
    text: "Order Book",
    style: {
      fontSize: '18px',
      fontWeight: 'bold',
      color: '#333'
    }
  },
  annotations: [{
    labels: [{
      point: { x: 0, y: 0 },
      text: 'Bids',
      backgroundColor: 'rgba(0, 120, 200, 0.8)',
      style: {
        color: "white",
        fontSize: '12px',
        fontWeight: 'bold'
      },
      shape: 'callout',
      y: -5
    },
    {
      point: { x: 100000, y: 0 },
      text: 'Asks',
      backgroundColor: 'rgba(200, 0, 0, 0.8)',
      style: {
        color: "white",
        fontSize: '12px',
        fontWeight: 'bold'
      },
      shape: 'callout',
      y: -5
    }]
  }],
  xAxis: {
    allowDecimals: false,
    tickInterval: 1,
    minPadding: 0.1,
    maxPadding: 0.1,
    labels: {
      formatter: function () {
        return Math.round(this.value + 0.5).toString();
      },
      align: 'center',
      x: 0,
      style: {
        color: '#666',
        fontSize: '11px'
      }
    },
    lineColor: '#ccd6eb',
    tickColor: '#ccd6eb'
  },
  yAxis: {
    labels: {
      format: "{value:.0f}",
      style: {
        color: '#666',
        fontSize: '11px'
      }
    },
    title: {
      text: "Volume",
      style: {
        color: '#666',
        fontSize: '12px'
      }
    },
    min: 0,
    gridLineColor: '#e6e6e6'
  },
  credits: {
    enabled: false
  },
  legend: {
    enabled: false
  },
  tooltip: {
    shared: true,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderWidth: 0,
    shadow: true,
    useHTML: true,
    headerFormat: '<table><tr><th colspan="2">{point.key:.2f}</th></tr>',
    pointFormat: '<tr><td style="color: {series.color}">{series.name}: </td>' +
      '<td style="text-align: right"><b>{point.y:.0f}</b></td></tr>',
    footerFormat: '</table>'
  },
  plotOptions: {
    column: {
      animation: false,
      pointPadding: 0.01,
      groupPadding: 0,
      borderWidth: 1,
      grouping: false
    }
  },
  series: chartData.value
});

watch(chartData, (newChartData) => {
  chartOptions.series = newChartData.map(series => ({
    ...series,
    pointPlacement: 0,
    color: series.name === "Bids" ? 'rgba(0, 120, 200, 0.8)' : 'rgba(200, 0, 0, 0.8)',
    borderColor: series.name === "Bids" ? 'rgba(0, 90, 150, 1)' : 'rgba(150, 0, 0, 1)'
  }));
}, { deep: true, immediate: true });

watchEffect(() => {
  chartOptions.xAxis.plotBands = [{
    from: -Infinity,
    to: midPoint.value,
    color: 'rgba(200, 230, 255, 0.2)'
  }, {
    from: midPoint.value,
    to: Infinity,
    color: 'rgba(255, 200, 200, 0.2)'
  }];
});
</script>

<style scoped>
.bid-ask-chart-container {
  width: 100%;
  height: 300px;
  background: linear-gradient(to bottom, #f8f9fa, #ffffff);
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 16px;
  transition: all 0.3s ease;
}

.bid-ask-chart-container:hover {
  box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}
</style>