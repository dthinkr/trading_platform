<template>
  <div class="relative">
    <!-- Number input -->
    <input
      v-if="field.type === 'number'"
      :value="value"
      @input="handleInput"
      type="number"
      :min="field.ge || field.gt || 0"
      :max="field.le || field.lt || undefined"
      :step="getStep(field)"
      :class="[
        'input text-xs py-1.5',
        isModified ? 'border-red-300 bg-red-50 focus:border-red-500 focus:ring-red-500' : ''
      ]"
    />
    
    <!-- Boolean input -->
    <div v-else-if="field.type === 'boolean'" class="flex items-center space-x-2">
      <input
        :checked="value"
        @change="handleBooleanChange"
        type="checkbox"
        :class="[
          'h-3 w-3 text-blue-600 rounded',
          isModified ? 'border-red-300' : 'border-neutral-300'
        ]"
      />
      <span class="text-xs text-neutral-700">{{ field.title }}</span>
    </div>
    
    <!-- Text area for admin users -->
    <textarea
      v-else-if="field.name === 'admin_users'"
      :value="value"
      @input="handleInput"
      rows="2"
      :class="[
        'input text-xs py-1.5 resize-none',
        isModified ? 'border-red-300 bg-red-50 focus:border-red-500 focus:ring-red-500' : ''
      ]"
      placeholder="Enter comma-separated usernames"
    ></textarea>
    
    <!-- Text input -->
    <input
      v-else
      :value="value"
      @input="handleInput"
      type="text"
      :class="[
        'input text-xs py-1.5',
        isModified ? 'border-red-300 bg-red-50 focus:border-red-500 focus:ring-red-500' : ''
      ]"
    />
    
    <!-- Modification indicator -->
    <div v-if="isModified" class="absolute right-2 top-1/2 transform -translate-y-1/2">
      <ExclamationCircleIcon class="h-3 w-3 text-red-500" aria-hidden="true" />
    </div>
    
    <!-- Field description tooltip -->
    <div v-if="field.description" class="mt-1">
      <p class="text-xs text-neutral-500">{{ field.description }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, defineEmits } from 'vue'
import { ExclamationCircleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  field: {
    type: Object,
    required: true
  },
  value: {
    required: true
  }
})

const emit = defineEmits(['update'])

// Check if field has been modified from default value
const isModified = computed(() => {
  return props.value !== props.field.default
})

// Get step value for number inputs
const getStep = (field) => {
  if (field.type === 'number') {
    if (field.name.includes('rate') || field.name.includes('prob') || field.name.includes('share')) {
      return 0.01
    }
    return 1
  }
  return undefined
}

// Handle input changes
const handleInput = (event) => {
  let value = event.target.value
  
  // Convert to number if it's a number field
  if (props.field.type === 'number') {
    value = parseFloat(value) || 0
  }
  
  emit('update', props.field.name, value)
}

// Handle boolean changes
const handleBooleanChange = (event) => {
  emit('update', props.field.name, event.target.checked)
}
</script> 