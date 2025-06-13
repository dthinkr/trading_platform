<template>
  <div class="card">
    <div class="card-header pb-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <DocumentDuplicateIcon class="h-4 w-4 text-blue-600" aria-hidden="true" />
          <h2 class="text-base font-semibold text-neutral-900">Log Files</h2>
        </div>
        <div class="text-xs text-neutral-500">
          {{ logFiles.length }} files
        </div>
      </div>
    </div>
    
    <div class="card-body p-4">
      <!-- Compact Action Buttons -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        <button 
          @click="downloadAllFiles" 
          class="btn btn-primary text-xs px-2 py-1.5 flex items-center justify-center"
        >
          <ArrowDownTrayIcon class="h-3 w-3 mr-1" aria-hidden="true" />
          All Files
        </button>

        <button 
          @click="downloadParameterHistory" 
          class="btn btn-secondary text-xs px-2 py-1.5 flex items-center justify-center"
        >
          <ClockIcon class="h-3 w-3 mr-1" aria-hidden="true" />
          Parameters
        </button>

        <button 
          @click="downloadQuestionnaireResponses" 
          class="btn btn-info text-xs px-2 py-1.5 flex items-center justify-center"
        >
          <ClipboardDocumentIcon class="h-3 w-3 mr-1" aria-hidden="true" />
          Questionnaire
        </button>

        <button 
          @click="downloadConsentData" 
          class="btn btn-success text-xs px-2 py-1.5 flex items-center justify-center"
        >
          <ClipboardDocumentCheckIcon class="h-3 w-3 mr-1" aria-hidden="true" />
          Consent
        </button>
      </div>

      <!-- Files List - Compact -->
      <div v-if="logFiles.length === 0" class="text-center py-6">
        <DocumentDuplicateIcon class="h-8 w-8 text-neutral-400 mx-auto mb-2" />
        <p class="text-xs text-neutral-500">No log files found</p>
      </div>
      
      <div v-else class="max-h-64 overflow-y-auto border border-neutral-200 rounded">
        <div v-for="(file, index) in logFiles" :key="file.name" 
             :class="['flex items-center justify-between px-3 py-2 text-xs hover:bg-neutral-25',
                      index !== logFiles.length - 1 ? 'border-b border-neutral-100' : '']">
          <div class="flex items-center min-w-0 flex-1 mr-3">
            <DocumentIcon class="h-3 w-3 text-neutral-400 mr-2 flex-shrink-0" aria-hidden="true" />
            <span class="font-mono text-neutral-900 truncate">{{ file.name }}</span>
          </div>
          <div class="flex space-x-1 flex-shrink-0">
            <button
              @click="downloadFile(file.name)"
              class="text-blue-600 hover:text-blue-800 p-1 rounded hover:bg-blue-50"
              :title="`Download ${file.name}`"
            >
              <ArrowDownTrayIcon class="h-3 w-3" aria-hidden="true" />
            </button>
            <button
              @click="confirmDeleteFile(file.name)"
              class="text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-50"
              :title="`Delete ${file.name}`"
            >
              <TrashIcon class="h-3 w-3" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg max-w-sm w-full">
        <div class="p-4">
          <div class="flex items-center mb-3">
            <ExclamationTriangleIcon class="h-5 w-5 text-red-600 mr-2" aria-hidden="true" />
            <h3 class="text-base font-semibold text-neutral-900">Confirm Delete</h3>
          </div>
          <p class="text-sm text-neutral-600 mb-4">
            Delete <strong class="font-mono">{{ fileToDelete }}</strong>?
          </p>
          <div class="flex space-x-2">
            <button
              @click="showDeleteDialog = false"
              class="btn btn-outline text-xs px-3 py-1.5 flex-1"
            >
              Cancel
            </button>
            <button
              @click="deleteFile"
              class="btn btn-danger text-xs px-3 py-1.5 flex-1"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { 
  DocumentDuplicateIcon, 
  DocumentIcon,
  ArrowDownTrayIcon, 
  ClockIcon, 
  ClipboardDocumentIcon,
  ClipboardDocumentCheckIcon,
  TrashIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'
import axios from '@/api/axios'

const logFiles = ref([])
const showDeleteDialog = ref(false)
const fileToDelete = ref(null)

const fetchLogFiles = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files`)
    logFiles.value = response.data.files || []
  } catch (error) {
    console.error("Failed to fetch log files:", error)
  }
}

const downloadFile = async (fileName) => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${fileName}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error("Error downloading file:", error)
  }
}

const confirmDeleteFile = (fileName) => {
  fileToDelete.value = fileName
  showDeleteDialog.value = true
}

const deleteFile = async () => {
  try {
    await axios.delete(`${import.meta.env.VITE_HTTP_URL}files/${fileToDelete.value}`)
    logFiles.value = logFiles.value.filter(file => file.name !== fileToDelete.value)
    showDeleteDialog.value = false
    fileToDelete.value = null
  } catch (error) {
    console.error("Error deleting file:", error)
  }
}

const downloadAllFiles = async () => {
  try {
    // Download all files individually
    for (const file of logFiles.value) {
      await downloadFile(file.name)
      // Add a small delay between downloads to prevent overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 100))
    }
  } catch (error) {
    console.error("Error downloading all files:", error)
  }
}

const downloadParameterHistory = async () => {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_HTTP_URL}admin/download_parameter_history`, 
      { responseType: 'blob' }
    )
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'parameter_history.json')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error("Error downloading parameter history:", error)
  }
}

const downloadQuestionnaireResponses = async () => {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_HTTP_URL}admin/download_questionnaire_responses`, 
      { responseType: 'blob' }
    )
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'questionnaire_responses.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error("Error downloading questionnaire responses:", error)
  }
}

const downloadConsentData = async () => {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_HTTP_URL}admin/download-consent-data`, 
      { responseType: 'blob' }
    )
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'consent_data.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error("Error downloading consent data:", error)
  }
}

onMounted(() => {
  fetchLogFiles()
})
</script>
