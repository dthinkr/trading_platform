<template>
  <div class="min-h-screen bg-neutral-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-neutral-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <CogIcon class="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <h1 class="text-xl font-semibold text-neutral-900">Trading Platform Admin</h1>
          </div>
          
          <div class="flex items-center space-x-4">
            <span class="text-sm text-neutral-600">
              {{ currentTime }}
            </span>
            <button
              @click="refreshData"
              :disabled="isLoading"
              class="btn btn-outline text-sm"
            >
              <ArrowPathIcon 
                :class="['h-4 w-4 mr-2', isLoading && 'animate-spin']" 
                aria-hidden="true" 
              />
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Quick Stats -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card">
          <div class="card-body">
            <div class="flex items-center">
              <div class="flex-1">
                <p class="text-sm font-medium text-neutral-600">Active Markets</p>
                <p class="text-2xl font-bold text-neutral-900">{{ stats.activeMarkets }}</p>
              </div>
              <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <ChartBarIcon class="h-6 w-6 text-blue-600" aria-hidden="true" />
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <div class="flex items-center">
              <div class="flex-1">
                <p class="text-sm font-medium text-neutral-600">Connected Traders</p>
                <p class="text-2xl font-bold text-neutral-900">{{ stats.connectedTraders }}</p>
              </div>
              <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <UsersIcon class="h-6 w-6 text-green-600" aria-hidden="true" />
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <div class="flex items-center">
              <div class="flex-1">
                <p class="text-sm font-medium text-neutral-600">Total Orders</p>
                <p class="text-2xl font-bold text-neutral-900">{{ stats.totalOrders }}</p>
              </div>
              <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <ClipboardDocumentListIcon class="h-6 w-6 text-purple-600" aria-hidden="true" />
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <div class="flex items-center">
              <div class="flex-1">
                <p class="text-sm font-medium text-neutral-600">System Status</p>
                <p class="text-sm font-semibold"
                   :class="stats.systemStatus === 'online' ? 'text-green-600' : 'text-red-600'">
                  {{ stats.systemStatus.toUpperCase() }}
                </p>
              </div>
              <div :class="[
                'w-12 h-12 rounded-lg flex items-center justify-center',
                stats.systemStatus === 'online' ? 'bg-green-100' : 'bg-red-100'
              ]">
                <ServerStackIcon 
                  :class="[
                    'h-6 w-6',
                    stats.systemStatus === 'online' ? 'text-green-600' : 'text-red-600'
                  ]" 
                  aria-hidden="true" 
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Active Markets -->
        <div class="lg:col-span-2">
          <div class="card">
            <div class="card-header">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
                  <BuildingOfficeIcon class="h-5 w-5 mr-2 text-blue-600" aria-hidden="true" />
                  Active Markets
                </h3>
                <button
                  @click="showCreateMarket = true"
                  class="btn btn-primary text-sm"
                >
                  <PlusIcon class="h-4 w-4 mr-2" />
                  Create Market
                </button>
              </div>
            </div>
            <div class="card-body">
              <div v-if="markets.length === 0" class="text-center py-8">
                <BuildingOfficeIcon class="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                <p class="text-neutral-500">No active markets</p>
                <button
                  @click="showCreateMarket = true"
                  class="btn btn-primary mt-4"
                >
                  Create Your First Market
                </button>
              </div>
              <div v-else class="space-y-4">
                <div
                  v-for="market in markets"
                  :key="market.id"
                  class="border border-neutral-200 rounded-lg p-4 hover:border-neutral-300 transition-colors"
                >
                  <div class="flex items-center justify-between">
                    <div class="flex-1">
                      <div class="flex items-center space-x-3">
                        <h4 class="font-medium text-neutral-900">{{ market.name }}</h4>
                        <span :class="[
                          'px-2 py-1 text-xs font-medium rounded-full',
                          market.status === 'active' ? 'bg-green-100 text-green-800' :
                          market.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-neutral-100 text-neutral-800'
                        ]">
                          {{ market.status }}
                        </span>
                      </div>
                      <div class="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span class="text-neutral-500">Traders:</span>
                          <span class="font-medium ml-1">{{ market.traders }}</span>
                        </div>
                        <div>
                          <span class="text-neutral-500">Duration:</span>
                          <span class="font-medium ml-1">{{ market.duration }}m</span>
                        </div>
                        <div>
                          <span class="text-neutral-500">Orders:</span>
                          <span class="font-medium ml-1">{{ market.orders }}</span>
                        </div>
                        <div>
                          <span class="text-neutral-500">Price:</span>
                          <span class="font-medium ml-1">${{ market.currentPrice }}</span>
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center space-x-2 ml-4">
                      <button
                        @click="viewMarket(market.id)"
                        class="btn btn-outline text-sm"
                      >
                        <EyeIcon class="h-4 w-4 mr-1" />
                        View
                      </button>
                      <button
                        v-if="market.status === 'active'"
                        @click="stopMarket(market.id)"
                        class="btn btn-danger text-sm"
                      >
                        <StopIcon class="h-4 w-4 mr-1" />
                        Stop
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- System Information & Actions -->
        <div class="space-y-6">
          <!-- System Health -->
          <div class="card">
            <div class="card-header">
              <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
                <HeartIcon class="h-5 w-5 mr-2 text-red-600" aria-hidden="true" />
                System Health
              </h3>
            </div>
            <div class="card-body space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-sm text-neutral-600">WebSocket Server</span>
                <span class="flex items-center text-sm">
                  <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  Online
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-neutral-600">Database</span>
                <span class="flex items-center text-sm">
                  <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  Connected
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-neutral-600">Order Processing</span>
                <span class="flex items-center text-sm">
                  <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  Normal
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-neutral-600">CPU Usage</span>
                <span class="text-sm text-neutral-900">{{ systemHealth.cpu }}%</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-neutral-600">Memory Usage</span>
                <span class="text-sm text-neutral-900">{{ systemHealth.memory }}%</span>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="card">
            <div class="card-header">
              <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
                <BoltIcon class="h-5 w-5 mr-2 text-yellow-600" aria-hidden="true" />
                Quick Actions
              </h3>
            </div>
            <div class="card-body space-y-3">
              <button class="btn btn-outline w-full justify-start">
                <DocumentArrowDownIcon class="h-4 w-4 mr-2" />
                Export Data
              </button>
              <button class="btn btn-outline w-full justify-start">
                <DocumentTextIcon class="h-4 w-4 mr-2" />
                View Logs
              </button>
              <button class="btn btn-outline w-full justify-start">
                <Cog6ToothIcon class="h-4 w-4 mr-2" />
                System Settings
              </button>
              <button class="btn btn-outline w-full justify-start">
                <UserGroupIcon class="h-4 w-4 mr-2" />
                Manage Users
              </button>
            </div>
          </div>

          <!-- Recent Activity -->
          <div class="card">
            <div class="card-header">
              <h3 class="text-lg font-semibold text-neutral-900 flex items-center">
                <ClockIcon class="h-5 w-5 mr-2 text-neutral-600" aria-hidden="true" />
                Recent Activity
              </h3>
            </div>
            <div class="card-body">
              <div class="space-y-3">
                <div
                  v-for="activity in recentActivity"
                  :key="activity.id"
                  class="flex items-start space-x-3 text-sm"
                >
                  <div :class="[
                    'w-2 h-2 rounded-full mt-2 flex-shrink-0',
                    activity.type === 'market' ? 'bg-blue-500' :
                    activity.type === 'user' ? 'bg-green-500' :
                    activity.type === 'system' ? 'bg-yellow-500' : 'bg-neutral-500'
                  ]"></div>
                  <div class="flex-1 min-w-0">
                    <p class="text-neutral-900">{{ activity.message }}</p>
                    <p class="text-neutral-500 text-xs">{{ activity.timestamp }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Market Modal -->
    <div v-if="showCreateMarket" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg max-w-md w-full">
        <div class="p-6">
          <h3 class="text-lg font-semibold text-neutral-900 mb-4">Create New Market</h3>
          <p class="text-sm text-neutral-600 mb-4">
            This will redirect you to the market creation interface.
          </p>
          <div class="flex space-x-3">
            <button
              @click="showCreateMarket = false"
              class="btn btn-outline flex-1"
            >
              Cancel
            </button>
            <button
              @click="navigateToMarketCreator"
              class="btn btn-primary flex-1"
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  CogIcon,
  ArrowPathIcon,
  ChartBarIcon,
  UsersIcon,
  ClipboardDocumentListIcon,
  ServerStackIcon,
  BuildingOfficeIcon,
  PlusIcon,
  EyeIcon,
  StopIcon,
  HeartIcon,
  BoltIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  UserGroupIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()

// State
const isLoading = ref(false)
const showCreateMarket = ref(false)
const currentTime = ref('')

// Mock data
const stats = ref({
  activeMarkets: 3,
  connectedTraders: 25,
  totalOrders: 1247,
  systemStatus: 'online'
})

const systemHealth = ref({
  cpu: 45,
  memory: 62
})

const markets = ref([
  {
    id: 1,
    name: 'Market Session Alpha',
    status: 'active',
    traders: 12,
    duration: 30,
    orders: 156,
    currentPrice: 102
  },
  {
    id: 2,
    name: 'Market Session Beta',
    status: 'pending',
    traders: 8,
    duration: 25,
    orders: 89,
    currentPrice: 98
  },
  {
    id: 3,
    name: 'Market Session Gamma',
    status: 'completed',
    traders: 15,
    duration: 35,
    orders: 203,
    currentPrice: 105
  }
])

const recentActivity = ref([
  {
    id: 1,
    type: 'market',
    message: 'Market Session Alpha started',
    timestamp: '2 minutes ago'
  },
  {
    id: 2,
    type: 'user',
    message: 'New trader joined Market Beta',
    timestamp: '5 minutes ago'
  },
  {
    id: 3,
    type: 'system',
    message: 'System backup completed',
    timestamp: '10 minutes ago'
  }
])

// Methods
function updateTime() {
  currentTime.value = new Date().toLocaleTimeString()
}

function refreshData() {
  isLoading.value = true
  setTimeout(() => {
    isLoading.value = false
  }, 1000)
}

function viewMarket(marketId) {
  router.push(`/admin/market/${marketId}`)
}

function stopMarket(marketId) {
  const market = markets.value.find(m => m.id === marketId)
  if (market) {
    market.status = 'completed'
  }
}

function navigateToMarketCreator() {
  showCreateMarket.value = false
  router.push('/market-creator')
}

// Lifecycle
let timeInterval
onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script> 