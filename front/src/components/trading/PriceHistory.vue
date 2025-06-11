<template>
  <div class="card">
    <div class="card-header">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
          <TrendingUpIcon class="h-5 w-5 mr-2 text-green-600" aria-hidden="true" />
          Price History
        </h3>
        <div class="flex items-center space-x-2">
          <select 
            v-model="timeRange" 
            class="input text-sm py-1 px-2"
            aria-label="Select time range"
          >
            <option value="1m">1 Min</option>
            <option value="5m">5 Min</option>
            <option value="15m">15 Min</option>
            <option value="1h">1 Hour</option>
          </select>
        </div>
      </div>
    </div>
    <div class="card-body">
      <div class="relative">
        <!-- Loading state -->
        <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
          <div class="spinner h-6 w-6 text-green-600"></div>
        </div>
        
        <!-- Chart container -->
        <div class="h-80 relative">
          <canvas 
            ref="chartCanvas" 
            class="w-full h-full"
            :aria-label="chartAriaLabel"
            role="img"
          ></canvas>
        </div>
        
        <!-- Price statistics -->
        <div class="flex justify-between items-center mt-4 text-sm">
          <div class="flex space-x-6">
            <div v-if="currentPrice" class="flex items-center">
              <span class="text-neutral-600 mr-1">Current:</span>
              <span class="font-semibold" :class="priceChangeClass">
                {{ formatPrice(currentPrice) }}
              </span>
            </div>
            <div v-if="priceChange" class="flex items-center">
              <span class="text-neutral-600 mr-1">Change:</span>
              <span class="font-semibold" :class="priceChangeClass">
                {{ priceChange > 0 ? '+' : '' }}{{ formatPrice(priceChange) }}
                ({{ formatPercentage(priceChangePercent) }}%)
              </span>
            </div>
          </div>
          <div class="flex space-x-4 text-xs text-neutral-500">
            <span v-if="highPrice">High: {{ formatPrice(highPrice) }}</span>
            <span v-if="lowPrice">Low: {{ formatPrice(lowPrice) }}</span>
          </div>
        </div>
        
        <!-- Error state -->
        <div v-if="error" class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div class="flex items-center">
            <ExclamationTriangleIcon class="h-5 w-5 text-red-400 mr-2" aria-hidden="true" />
            <span class="text-sm text-red-800">{{ error }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { TrendingUpIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const tradingStore = useTradingStore()
const chartCanvas = ref(null)
const timeRange = ref('5m')
const isLoading = ref(true)
const error = ref('')
let chart = null
let resizeObserver = null

// Computed properties
const priceHistory = computed(() => tradingStore.priceHistory || [])
const currentPrice = computed(() => tradingStore.currentPrice)

const chartAriaLabel = computed(() => {
  const points = filteredPriceHistory.value.length
  return `Price history chart showing ${points} data points over ${timeRange.value}`
})

const filteredPriceHistory = computed(() => {
  const now = Date.now()
  const ranges = {
    '1m': 60 * 1000,
    '5m': 5 * 60 * 1000,
    '15m': 15 * 60 * 1000,
    '1h': 60 * 60 * 1000
  }
  
  const rangeMs = ranges[timeRange.value] || ranges['5m']
  const cutoff = now - rangeMs
  
  return priceHistory.value.filter(point => 
    new Date(point.timestamp).getTime() >= cutoff
  ).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
})

const priceChange = computed(() => {
  const history = filteredPriceHistory.value
  if (history.length < 2) return null
  
  const firstPrice = history[0].price
  const lastPrice = history[history.length - 1].price
  return lastPrice - firstPrice
})

const priceChangePercent = computed(() => {
  const history = filteredPriceHistory.value
  if (history.length < 2) return null
  
  const firstPrice = history[0].price
  const change = priceChange.value
  return (change / firstPrice) * 100
})

const priceChangeClass = computed(() => {
  const change = priceChange.value
  if (change === null || change === 0) return 'text-neutral-700'
  return change > 0 ? 'text-green-600' : 'text-red-600'
})

const highPrice = computed(() => {
  const history = filteredPriceHistory.value
  if (history.length === 0) return null
  return Math.max(...history.map(p => p.price))
})

const lowPrice = computed(() => {
  const history = filteredPriceHistory.value
  if (history.length === 0) return null
  return Math.min(...history.map(p => p.price))
})

const chartData = computed(() => {
  const history = filteredPriceHistory.value
  
  if (history.length === 0) {
    return { labels: [], datasets: [] }
  }

  const labels = history.map(point => 
    new Date(point.timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  )
  
  const prices = history.map(point => point.price)
  const volumes = history.map(point => point.volume || 0)

  return {
    labels,
    datasets: [
      {
        label: 'Price',
        data: prices,
        borderColor: 'rgb(59, 130, 246)', // blue-500
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
        pointRadius: 2,
        pointHoverRadius: 4,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: 'white',
        pointBorderWidth: 1,
      }
    ]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index'
  },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      titleColor: 'rgb(55, 65, 81)',
      bodyColor: 'rgb(55, 65, 81)',
      borderColor: 'rgb(229, 231, 235)',
      borderWidth: 1,
      cornerRadius: 8,
      displayColors: false,
      callbacks: {
        title: function(context) {
          return `Time: ${context[0].label}`
        },
        label: function(context) {
          return `Price: ${formatPrice(context.parsed.y)}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      },
      ticks: {
        maxTicksLimit: 8,
        color: 'rgb(107, 114, 128)',
        font: {
          size: 11,
          family: 'Inter'
        }
      }
    },
    y: {
      beginAtZero: false,
      grid: {
        color: 'rgba(229, 231, 235, 0.5)'
      },
      ticks: {
        color: 'rgb(107, 114, 128)',
        font: {
          size: 11,
          family: 'Inter'
        },
        callback: function(value) {
          return formatPrice(value)
        }
      },
      title: {
        display: true,
        text: 'Price',
        color: 'rgb(107, 114, 128)',
        font: {
          size: 12,
          family: 'Inter',
          weight: '500'
        }
      }
    }
  },
  animation: {
    duration: 300,
    easing: 'easeInOutQuart'
  }
}))

// Methods
function formatPrice(price) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(price)
}

function formatPercentage(percent) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(percent)
}

function initChart() {
  if (!chartCanvas.value) return

  try {
    const ctx = chartCanvas.value.getContext('2d')
    
    if (chart) {
      chart.destroy()
    }

    chart = new ChartJS(ctx, {
      type: 'line',
      data: chartData.value,
      options: chartOptions.value
    })

    isLoading.value = false
    error.value = ''
  } catch (err) {
    console.error('Failed to initialize chart:', err)
    error.value = 'Failed to load chart'
    isLoading.value = false
  }
}

function updateChart() {
  if (!chart) return

  try {
    chart.data = chartData.value
    chart.options = chartOptions.value
    chart.update('none')
  } catch (err) {
    console.error('Failed to update chart:', err)
    error.value = 'Failed to update chart'
  }
}

function handleResize() {
  if (chart) {
    chart.resize()
  }
}

// Watchers
watch([chartData, timeRange], () => {
  if (chart) {
    updateChart()
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  await nextTick()
  
  initChart()
  
  if (chartCanvas.value && ResizeObserver) {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(chartCanvas.value.parentElement)
  }
})

onUnmounted(() => {
  if (chart) {
    chart.destroy()
    chart = null
  }
  
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})
</script>

<style scoped>
canvas {
  max-height: 20rem; /* h-80 */
}
</style> 