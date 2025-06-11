<template>
  <div class="card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
        <ChartBarIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
        Order Book
      </h3>
    </div>
    <div class="card-body">
      <div class="relative">
        <!-- Loading state -->
        <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
          <div class="spinner h-6 w-6 text-blue-600"></div>
        </div>
        
        <!-- Chart container -->
        <div class="h-64 relative">
          <canvas 
            ref="chartCanvas" 
            class="w-full h-full"
            :aria-label="chartAriaLabel"
            role="img"
          ></canvas>
        </div>
        
        <!-- Chart legend -->
        <div class="flex justify-center mt-4 space-x-6 text-sm">
          <div class="flex items-center">
            <div class="w-3 h-3 bg-blue-500 rounded mr-2"></div>
            <span class="text-neutral-700">Bids</span>
          </div>
          <div class="flex items-center">
            <div class="w-3 h-3 bg-red-500 rounded mr-2"></div>
            <span class="text-neutral-700">Asks</span>
          </div>
          <div v-if="midPoint" class="flex items-center">
            <div class="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
            <span class="text-neutral-700">Midpoint: {{ formatPrice(midPoint) }}</span>
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
import { ChartBarIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useTradingStore } from '@/stores/trading'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement
)

const tradingStore = useTradingStore()
const chartCanvas = ref(null)
const isLoading = ref(true)
const error = ref('')
let chart = null
let resizeObserver = null

// Computed properties
const orderBook = computed(() => tradingStore.orderBook)
const midPoint = computed(() => tradingStore.midPoint)

const chartAriaLabel = computed(() => {
  const bidCount = orderBook.value.bids?.length || 0
  const askCount = orderBook.value.asks?.length || 0
  return `Order book chart showing ${bidCount} bid levels and ${askCount} ask levels`
})

const chartData = computed(() => {
  const bids = orderBook.value.bids || []
  const asks = orderBook.value.asks || []
  
  if (bids.length === 0 && asks.length === 0) {
    return { labels: [], datasets: [] }
  }

  // Combine and sort all price levels
  const allPrices = [
    ...bids.map(bid => ({ price: bid.x, volume: bid.y, type: 'bid' })),
    ...asks.map(ask => ({ price: ask.x, volume: ask.y, type: 'ask' }))
  ].sort((a, b) => a.price - b.price)

  const labels = allPrices.map(item => formatPrice(item.price))
  
  // Create datasets for bids and asks
  const bidData = allPrices.map(item => item.type === 'bid' ? item.volume : 0)
  const askData = allPrices.map(item => item.type === 'ask' ? item.volume : 0)

  return {
    labels,
    datasets: [
      {
        label: 'Bids',
        data: bidData,
        backgroundColor: 'rgba(59, 130, 246, 0.7)', // blue-500 with opacity
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
        barThickness: 'flex',
        maxBarThickness: 40,
      },
      {
        label: 'Asks',
        data: askData,
        backgroundColor: 'rgba(239, 68, 68, 0.7)', // red-500 with opacity
        borderColor: 'rgb(239, 68, 68)',
        borderWidth: 1,
        barThickness: 'flex',
        maxBarThickness: 40,
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
      display: false // We use custom legend
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      titleColor: 'rgb(55, 65, 81)',
      bodyColor: 'rgb(55, 65, 81)',
      borderColor: 'rgb(229, 231, 235)',
      borderWidth: 1,
      cornerRadius: 8,
      displayColors: true,
      callbacks: {
        title: function(context) {
          return `Price: ${context[0].label}`
        },
        label: function(context) {
          const value = context.parsed.y
          if (value === 0) return null
          return `${context.dataset.label}: ${value} shares`
        }
      }
    }
  },
  scales: {
    x: {
      stacked: false,
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
      stacked: false,
      beginAtZero: true,
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
          return value.toLocaleString()
        }
      },
      title: {
        display: true,
        text: 'Volume (Shares)',
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
    maximumFractionDigits: 0
  }).format(Math.round(price))
}

function initChart() {
  if (!chartCanvas.value) return

  try {
    const ctx = chartCanvas.value.getContext('2d')
    
    if (chart) {
      chart.destroy()
    }

    chart = new ChartJS(ctx, {
      type: 'bar',
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
    chart.update('none') // Update without animation for better performance
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
watch(chartData, () => {
  if (chart) {
    updateChart()
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  await nextTick()
  
  // Initialize chart
  initChart()
  
  // Set up resize observer for responsive behavior
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
/* Ensure canvas maintains aspect ratio */
canvas {
  max-height: 16rem; /* 64 * 0.25rem = 16rem = h-64 */
}
</style> 