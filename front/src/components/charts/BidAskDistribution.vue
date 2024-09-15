<template>
  <v-card class="bid-ask-chart-container" elevation="3">
    <v-card-title class="cardtitle-primary">
      <v-icon left>mdi-chart-bar</v-icon>
      Bid-Ask Distribution
    </v-card-title>
    <div class="chart-wrapper">
      <highcharts-chart
        :constructor-type="'chart'"
        :options="chartOptions"
        :deepCopyOnUpdate="true"
      ></highcharts-chart>
    </div>
    
  </v-card>
</template>

<script setup>
import { reactive, watchEffect } from "vue";
import { useTraderStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { Chart as HighchartsChart } from "highcharts-vue";
import Highcharts from 'highcharts';
import AnnotationsModule from 'highcharts/modules/annotations';

AnnotationsModule(Highcharts);

const { chartData, midPoint } = storeToRefs(useTraderStore());

console.log('chartData:', chartData.value);
console.log('midPoint:', midPoint.value);

const chartOptions = reactive({
  chart: {
    type: "column",
    animation: false,
    backgroundColor: '#f5f5f5',
    style: {
      fontFamily: 'Roboto, Arial, sans-serif'
    },
    height: 250
  },
  title: {
    text: null
  },
  annotations: [{
    labels: [{
      point: { x: 0, y: 0 },
      text: 'Bids',
      backgroundColor: 'rgba(33, 150, 243, 0.8)',
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
      backgroundColor: 'rgba(244, 67, 54, 0.8)',
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
        return this.value.toString();
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

watchEffect(() => {
  console.log('watchEffect triggered');
  console.log('Updated chartData:', chartData.value);
  console.log('Updated midPoint:', midPoint.value);

  chartOptions.series = chartData.value.map(series => ({
    ...series,
    pointPlacement: 0,
    color: series.name === "Bids" ? 'rgba(33, 150, 243, 0.8)' : 'rgba(244, 67, 54, 0.8)',
    borderColor: series.name === "Bids" ? 'rgba(25, 118, 210, 1)' : 'rgba(211, 47, 47, 1)'
  }));

  chartOptions.xAxis.plotBands = [{
    from: -Infinity,
    to: midPoint.value,
    color: 'rgba(33, 150, 243, 0.1)'
  }, {
    from: midPoint.value,
    to: Infinity,
    color: 'rgba(244, 67, 54, 0.1)'
  }];
});
</script>

<style scoped>
.bid-ask-chart-container {
  width: 100%;
  background-color: #f5f5f5;
}

.chart-wrapper {
  padding: 16px;
}


.cardtitle-primary {
  color: black;
  font-weight: bold;
  padding: 12px 16px;
}

.bid-ask-chart-container:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  transition: all 0.3s ease;
}
</style>