<template>
  <v-card elevation="1">
    <v-card-title class="compact-title">
      <v-icon left color="deep-blue" size="18">mdi-file-document-multiple-outline</v-icon>
      Data Export
    </v-card-title>
    <v-card-text class="pa-3">
      <v-btn
        color="primary"
        @click="downloadAllFiles"
        block
        variant="elevated"
        class="mb-2 custom-btn download-all-btn"
        size="small"
      >
        <v-icon start size="16">mdi-download-multiple</v-icon>
        Download All Files
      </v-btn>

      <v-row dense class="mb-2">
        <v-col cols="4">
          <v-btn
            color="secondary"
            @click="downloadParameterHistory"
            block
            variant="outlined"
            class="custom-btn"
            size="x-small"
          >
            <v-icon size="14">mdi-history</v-icon>
          </v-btn>
        </v-col>
        <v-col cols="4">
          <v-btn
            color="info"
            @click="downloadQuestionnaireResponses"
            block
            variant="outlined"
            class="custom-btn"
            size="x-small"
          >
            <v-icon size="14">mdi-clipboard-text</v-icon>
          </v-btn>
        </v-col>
        <v-col cols="4">
          <v-btn
            color="success"
            @click="downloadConsentData"
            block
            variant="outlined"
            class="custom-btn"
            size="x-small"
          >
            <v-icon size="14">mdi-clipboard-check</v-icon>
          </v-btn>
        </v-col>
      </v-row>

      <v-data-table
        :headers="[
          { title: 'File Name', key: 'name' },
          { title: 'Actions', key: 'actions', sortable: false },
        ]"
        :items="logFiles"
        :items-per-page="4"
        density="compact"
        class="compact-table"
      >
        <template v-slot:item.actions="{ item }">
          <v-btn icon size="x-small" color="primary" @click="downloadFile(item.name)" class="mr-1" variant="outlined">
            <v-icon size="14">mdi-download</v-icon>
          </v-btn>
          <v-btn icon size="x-small" color="error" @click="confirmDeleteFile(item.name)" variant="outlined">
            <v-icon size="14">mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>

    <v-dialog v-model="showDeleteDialog" max-width="300px">
      <v-card>
        <v-card-title class="compact-title">Confirm Delete</v-card-title>
        <v-card-text class="pa-3">Are you sure you want to delete this file?</v-card-text>
        <v-card-actions class="pa-3">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="outlined" @click="showDeleteDialog = false" class="custom-btn" size="small"
            >Cancel</v-btn
          >
          <v-btn color="error" variant="elevated" @click="deleteFile" class="custom-btn ml-2" size="small">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/api/axios'
import { saveAs } from 'file-saver'
import JSZip from 'jszip'

const logFiles = ref([])
const showDeleteDialog = ref(false)
const fileToDelete = ref(null)

const fetchLogFiles = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files`)
    logFiles.value = response.data.files
  } catch (error) {
    console.error('Failed to fetch log files:', error)
  }
}

const downloadFile = async (fileName) => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${fileName}`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error downloading file:', error)
  }
}

const confirmDeleteFile = (fileName) => {
  fileToDelete.value = fileName
  showDeleteDialog.value = true
}

const deleteFile = async () => {
  try {
    await axios.delete(`${import.meta.env.VITE_HTTP_URL}files/${fileToDelete.value}`)
    logFiles.value = logFiles.value.filter((file) => file.name !== fileToDelete.value)
    showDeleteDialog.value = false
    fileToDelete.value = null
  } catch (error) {
    console.error('Error deleting file:', error)
  }
}

const downloadAllFiles = async () => {
  try {
    const zip = new JSZip()

    for (const file of logFiles.value) {
      const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${file.name}`, {
        responseType: 'blob',
      })
      zip.file(file.name, response.data)
    }

    const content = await zip.generateAsync({ type: 'blob' })
    saveAs(content, 'all_log_files.zip')
  } catch (error) {
    console.error('Error downloading all files:', error)
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
  } catch (error) {
    console.error('Error downloading parameter history:', error)
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
  } catch (error) {
    console.error('Error downloading questionnaire responses:', error)
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
  } catch (error) {
    console.error('Error downloading consent data:', error)
  }
}

onMounted(() => {
  fetchLogFiles()
})
</script>

<style scoped>
.compact-title {
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.75rem !important;
  background: rgba(248, 250, 252, 0.8);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  color: #1e293b !important;
}

.compact-table {
  font-size: 0.85rem;
  font-family: 'Inter', sans-serif;
}

:deep(.v-data-table-header th) {
  font-size: 0.8rem !important;
  padding: 0.5rem !important;
  font-weight: 600 !important;
}

:deep(.v-data-table tbody td) {
  padding: 0.25rem 0.5rem !important;
  font-size: 0.85rem !important;
}

.deep-blue {
  color: #1a237e !important;
}

.custom-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: 0.5px !important;
  font-family: 'Inter', sans-serif !important;
}

.v-btn.v-btn--icon.v-size--x-small {
  width: 20px;
  height: 20px;
  margin: 0 1px;
}

.v-btn.v-btn--icon.v-size--x-small .v-icon {
  font-size: 14px;
}

.download-all-btn {
  font-weight: 600 !important;
}
</style>
