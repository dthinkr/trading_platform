<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <ChartBarIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Order Book
      </h3>
    </div>
    <div class="card-body">
      <div class="h-64 flex items-center justify-center">
        <canvas ref="chartCanvas" class="w-full h-full"></canvas>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'

const tradingStore = useTradingStore()
const chartCanvas = ref(null)
let chart = null

// Simple placeholder - in a real implementation, you'd use Chart.js
onMounted(() => {
  if (chartCanvas.value) {
    const ctx = chartCanvas.value.getContext('2d')
    ctx.fillStyle = '#e5e7eb'
    ctx.fillRect(0, 0, chartCanvas.value.width, chartCanvas.value.height)
    ctx.fillStyle = '#6b7280'
    ctx.font = '16px Inter'
    ctx.textAlign = 'center'
    ctx.fillText('Order Book Chart', chartCanvas.value.width / 2, chartCanvas.value.height / 2)
  }
})

onUnmounted(() => {
  if (chart) {
    chart.destroy()
  }
})
</script> 