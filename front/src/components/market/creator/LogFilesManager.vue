<template>
  <v-card elevation="2">
    <v-card-title class="headline">
      <v-icon left color="deep-blue">mdi-file-document-multiple-outline</v-icon>
      Log Files
    </v-card-title>
    <v-card-text class="pa-2">
      <v-btn
        color="primary"
        @click="downloadAllFiles"
        block
        elevation="2"
        class="mb-2 custom-btn download-all-btn"
        x-large
      >
        <v-icon left large>mdi-download-multiple</v-icon>
        Download All Files
      </v-btn>

      <v-btn
        color="secondary"
        @click="downloadParameterHistory"
        block
        elevation="2"
        class="mb-2 custom-btn"
        x-large
      >
        <v-icon left large>mdi-history</v-icon>
        Download Parameter History
      </v-btn>

      <v-btn
        color="info"
        @click="downloadQuestionnaireResponses"
        block
        elevation="2"
        class="mb-2 custom-btn"
        x-large
      >
        <v-icon left large>mdi-clipboard-text</v-icon>
        Download Questionnaire Responses
      </v-btn>

      <v-btn
        color="success"
        @click="downloadConsentData"
        block
        elevation="2"
        class="mb-2 custom-btn"
        x-large
      >
        <v-icon left large>mdi-clipboard-check</v-icon>
        Download Consent Data
      </v-btn>

      <v-data-table
        :headers="[
          { text: 'File Name', value: 'name', class: 'custom-header' },
          { text: 'Actions', value: 'actions', sortable: false, class: 'custom-header' },
        ]"
        :items="logFiles"
        :items-per-page="5"
        class="elevation-1 custom-table"
        dense
      >
        <template v-slot:item.actions="{ item }">
          <v-btn icon x-small color="primary" @click="downloadFile(item.name)" class="mr-2">
            <v-icon small>mdi-download</v-icon>
          </v-btn>
          <v-btn icon x-small color="error" @click="confirmDeleteFile(item.name)">
            <v-icon small>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>

    <v-dialog v-model="showDeleteDialog" max-width="300px">
      <v-card>
        <v-card-title class="headline">Confirm Delete</v-card-title>
        <v-card-text>Are you sure you want to delete this file?</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey darken-1" text @click="showDeleteDialog = false" class="custom-btn"
            >Cancel</v-btn
          >
          <v-btn color="error" text @click="deleteFile" class="custom-btn">Delete</v-btn>
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
.headline {
  font-size: 1.35rem;
  font-weight: 600;
  color: #2c3e50;
  font-family: 'Inter', sans-serif;
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

.custom-table {
  font-family: 'Inter', sans-serif;
}

.custom-table :deep(.v-data-table__wrapper) {
  font-family: 'Inter', sans-serif;
}

.custom-header {
  font-weight: 600 !important;
  font-size: 0.81rem !important;
  color: #2c3e50 !important;
}

.v-data-table :deep(td) {
  padding: 0 7px !important;
}

.v-data-table :deep(.v-data-table__wrapper > table > tbody > tr > td:last-child) {
  width: 1%;
  white-space: nowrap;
}

.v-btn.v-btn--icon.v-size--x-small {
  width: 22px;
  height: 22px;
  margin: 0 2px;
}

.v-btn.v-btn--icon.v-size--x-small .v-icon {
  font-size: 14px;
}

.download-all-btn {
  font-size: 1.1rem !important;
  height: 48px !important;
  margin-bottom: 8px !important;
}

.download-all-btn .v-icon {
  font-size: 1.3rem !important;
  margin-right: 8px !important;
}
</style>
