<template>
  <div class="space-y-6">
    <!-- Instructions header -->
    <div class="text-center">
      <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <AcademicCapIcon class="h-8 w-8 text-green-600" aria-hidden="true" />
      </div>
      <h3 class="text-2xl font-bold text-neutral-900 mb-2">
        Trading Platform Guide
      </h3>
      <p class="text-lg text-neutral-600">
        Learn how the trading platform works before you start
      </p>
    </div>

    <!-- What is the Trading Platform -->
    <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
      <div class="flex items-center mb-3">
        <ComputerDesktopIcon class="h-6 w-6 text-blue-600 mr-2" aria-hidden="true" />
        <h4 class="text-lg font-semibold text-blue-900">What is the Trading Platform?</h4>
      </div>
      <div class="space-y-3 text-blue-800">
        <p class="text-sm">
          The trading platform is software that allows participants to trade with one another. 
          It displays relevant information about the demand and supply of an asset (e.g. a share). 
          What you see on the trading platform is common knowledge, meaning all other participants can see it.
        </p>
        <p class="text-sm">
          This trading platform closely replicates real financial exchange platforms, where participants trade under a double auction setting.
          In particular, a double auction trading mechanism allows buyers to submit bids (buy offers) and sellers to submit asks (sell offers) simultaneously. 
          The platform matches buyers and sellers based on price and quantity.
        </p>
        <p class="text-sm font-medium">
          Please take some time to carefully read the next sections.
        </p>
      </div>
    </div>

    <!-- Order Types -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Direct Orders -->
      <div class="bg-green-50 rounded-lg p-6 border border-green-200">
        <div class="flex items-center mb-3">
          <CurrencyDollarIcon class="h-6 w-6 text-green-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-green-900">Direct Orders</h4>
        </div>
        <div class="space-y-3 text-green-800">
          <p class="text-sm">
            You can directly accept an existing price to sell or buy, such as an order from another participant. 
            In this case, the trade is immediately executed at the best bid or ask respectively.
          </p>
        </div>
      </div>

      <!-- Passive Orders -->
      <div class="bg-purple-50 rounded-lg p-6 border border-purple-200">
        <div class="flex items-center mb-3">
          <ChartBarIcon class="h-6 w-6 text-purple-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-purple-900">Passive Orders</h4>
        </div>
        <div class="space-y-3 text-purple-800">
          <p class="text-sm">
            You can place orders to sell or buy that are not immediately executed. 
            This means you have to wait for someone to accept them.
          </p>
        </div>
      </div>
    </div>

    <!-- Improving Orders -->
    <div class="bg-orange-50 rounded-lg p-6 border border-orange-200">
      <div class="flex items-center mb-3">
        <WalletIcon class="h-6 w-6 text-orange-600 mr-2" aria-hidden="true" />
        <h4 class="text-lg font-semibold text-orange-900">Improving Orders</h4>
      </div>
      <div class="space-y-3 text-orange-800">
        <ul class="text-sm space-y-2 list-disc list-inside">
          <li>Place an order to sell (ask) a share for a lower price than the current best ask</li>
          <li>Place an order to buy (bid) a share for a higher price than the current best bid</li>
        </ul>
      </div>
    </div>

    <!-- Key concepts -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Order Book -->
      <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <div class="flex items-center mb-3">
          <BookOpenIcon class="h-6 w-6 text-blue-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-blue-900">Order Book</h4>
        </div>
        <div class="space-y-3 text-blue-800">
          <p class="text-sm">
            The order book shows all pending buy (bid) and sell (ask) orders in the market.
          </p>
          <ul class="text-sm space-y-1 list-disc list-inside">
            <li><strong>Bids:</strong> Orders to buy shares at specific prices</li>
            <li><strong>Asks:</strong> Orders to sell shares at specific prices</li>
            <li><strong>Spread:</strong> Difference between highest bid and lowest ask</li>
          </ul>
        </div>
      </div>

      <!-- Your Portfolio -->
      <div class="bg-orange-50 rounded-lg p-6 border border-orange-200">
        <div class="flex items-center mb-3">
          <WalletIcon class="h-6 w-6 text-orange-600 mr-2" aria-hidden="true" />
          <h4 class="text-lg font-semibold text-orange-900">Your Portfolio</h4>
        </div>
        <div class="space-y-3 text-orange-800">
          <p class="text-sm">
            Track your cash, shares, and overall performance.
          </p>
          <ul class="text-sm space-y-1 list-disc list-inside">
            <li><strong>Cash:</strong> Available money for buying shares</li>
            <li><strong>Shares:</strong> Number of shares you own</li>
            <li><strong>P&L:</strong> Profit and Loss from your trading</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Trading interface preview -->
    <div class="border border-neutral-200 rounded-lg overflow-hidden">
      <div class="bg-neutral-50 px-4 py-3 border-b border-neutral-200">
        <h4 class="font-semibold text-neutral-900 flex items-center">
          <ComputerDesktopIcon class="h-5 w-5 mr-2" aria-hidden="true" />
          Trading Platform Preview
        </h4>
        <p class="text-sm text-neutral-600 mt-1">
          This demonstration shows the trading platform in action with live components.
        </p>
      </div>
      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div class="bg-white border border-neutral-200 rounded-lg p-4">
            <h5 class="font-medium text-neutral-900 mb-2">Order Book</h5>
            <div class="space-y-1">
              <div class="flex justify-between text-red-600">
                <span>Ask: $105</span>
                <span>10 shares</span>
              </div>
              <div class="flex justify-between text-red-600">
                <span>Ask: $104</span>
                <span>15 shares</span>
              </div>
              <div class="border-t border-neutral-200 my-1"></div>
              <div class="flex justify-between text-blue-600">
                <span>Bid: $103</span>
                <span>12 shares</span>
              </div>
              <div class="flex justify-between text-blue-600">
                <span>Bid: $102</span>
                <span>8 shares</span>
              </div>
            </div>
          </div>
          
          <div class="bg-white border border-neutral-200 rounded-lg p-4">
            <h5 class="font-medium text-neutral-900 mb-2">Trading Panel</h5>
            <div class="space-y-2">
              <div class="flex space-x-2">
                <button class="flex-1 px-3 py-1 bg-blue-100 text-blue-800 rounded text-xs">Buy</button>
                <button class="flex-1 px-3 py-1 bg-neutral-100 text-neutral-600 rounded text-xs">Sell</button>
              </div>
              <input placeholder="Price: $103" class="w-full px-2 py-1 border border-neutral-300 rounded text-xs" readonly />
              <input placeholder="Quantity: 1" class="w-full px-2 py-1 border border-neutral-300 rounded text-xs" readonly />
              <button class="w-full px-3 py-1 bg-blue-600 text-white rounded text-xs">Place Order</button>
            </div>
          </div>
          
          <div class="bg-white border border-neutral-200 rounded-lg p-4">
            <h5 class="font-medium text-neutral-900 mb-2">Your Portfolio</h5>
            <div class="space-y-1 text-xs">
              <div class="flex justify-between">
                <span>Cash:</span>
                <span class="font-medium">$10,000</span>
              </div>
              <div class="flex justify-between">
                <span>Shares:</span>
                <span class="font-medium">50</span>
              </div>
              <div class="flex justify-between">
                <span>P&L:</span>
                <span class="font-medium text-green-600">+$150</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Trading rules -->
    <div class="bg-yellow-50 rounded-lg p-6 border border-yellow-200">
      <h4 class="font-semibold text-yellow-900 mb-3 flex items-center">
        <ExclamationTriangleIcon class="h-5 w-5 mr-2" aria-hidden="true" />
        Important Trading Rules
      </h4>
      <div class="grid gap-4 md:grid-cols-2 text-yellow-800">
        <ul class="space-y-2 text-sm list-disc list-inside">
          <li>You can only buy if you have sufficient cash</li>
          <li>You can only sell shares that you own</li>
          <li>Orders can be cancelled before they execute</li>
          <li>Market prices update in real-time</li>
        </ul>
        <ul class="space-y-2 text-sm list-disc list-inside">
          <li>Your goal may be to maximize profit or reach specific targets</li>
          <li>Pay attention to market trends and other traders</li>
          <li>Time is limited - plan your strategy accordingly</li>
          <li>All transactions are final once executed</li>
        </ul>
      </div>
    </div>

    <!-- Confirmation -->
    <div class="flex items-center justify-center">
      <label class="flex items-center space-x-3 cursor-pointer">
        <input
          type="checkbox"
          v-model="understood"
          @change="$emit('update:understood', understood)"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-neutral-300 rounded"
        />
        <span class="text-sm text-neutral-700">
          I understand how the trading platform works and am ready to proceed
        </span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  AcademicCapIcon,
  BookOpenIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  WalletIcon,
  ComputerDesktopIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  understood: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:understood'])

const understood = ref(props.understood)
</script> 