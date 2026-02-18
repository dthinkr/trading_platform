<template>
  <div class="log-files-manager">
    <header class="tp-card-header">
      <h2 class="tp-card-title">Data Export</h2>
      <div class="view-toggle">
        <button 
          class="toggle-btn" 
          :class="{ active: viewMode === 'grid' }"
          @click="viewMode = 'grid'"
        >
          <v-icon size="14">mdi-grid</v-icon>
        </button>
        <button 
          class="toggle-btn" 
          :class="{ active: viewMode === 'list' }"
          @click="viewMode = 'list'"
        >
          <v-icon size="14">mdi-format-list-bulleted</v-icon>
        </button>
      </div>
    </header>

    <div class="tp-card-body">
      <button class="tp-btn tp-btn-primary mb-3" style="width: 100%" @click="downloadAllFiles">
        Download All Files
      </button>

      <div class="quick-actions mb-3">
        <button class="tp-btn tp-btn-secondary tp-btn-sm" @click="downloadParameterHistory" title="Parameter History">
          <v-icon size="14">mdi-history</v-icon>
        </button>
        <button class="tp-btn tp-btn-secondary tp-btn-sm" @click="downloadQuestionnaireResponses" title="Questionnaire">
          <v-icon size="14">mdi-clipboard-text</v-icon>
        </button>
        <button class="tp-btn tp-btn-secondary tp-btn-sm" @click="downloadConsentData" title="Consent Data">
          <v-icon size="14">mdi-clipboard-check</v-icon>
        </button>
      </div>

      <!-- Grid View (Heatmap) -->
      <div v-if="viewMode === 'grid'" class="grid-view">
        <div v-if="groupedData.sessions.length > 0" class="session-grid">
          <table class="heatmap-table">
            <thead>
              <tr>
                <th class="session-header">Session</th>
                <th class="time-header">Time</th>
                <th v-for="m in marketColumns" :key="m" class="market-header">M{{ m }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="session in groupedData.sessions" :key="session.session_id">
                <td class="session-cell" :title="session.session_id">{{ formatSessionId(session.session_id) }}</td>
                <td class="time-cell">{{ formatSessionTime(session.session_id) }}</td>
                <td 
                  v-for="m in marketColumns" 
                  :key="m" 
                  class="market-cell" 
                  :class="{ 'has-file': session.markets[m], 'no-file': !session.markets[m] }" 
                  @click="session.markets[m] && downloadFile(session.markets[m])" 
                  :title="session.markets[m] || 'No file'"
                >
                  <v-icon v-if="session.markets[m]" size="14" color="white">mdi-download</v-icon>
                  <span v-else class="no-file-indicator">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="groupedData.ungrouped.length > 0" class="ungrouped-section">
          <span class="tp-label">Other Files ({{ groupedData.ungrouped.length }})</span>
          <div class="ungrouped-chips">
            <span 
              v-for="file in groupedData.ungrouped" 
              :key="file" 
              class="tp-badge file-badge"
              @click="downloadFile(file)"
            >
              {{ truncateFilename(file) }}
            </span>
          </div>
        </div>

        <div v-if="groupedData.sessions.length === 0 && groupedData.ungrouped.length === 0" class="no-data">
          No log files found
        </div>
      </div>

      <!-- List View -->
      <div v-else class="list-view">
        <v-data-table
          :headers="[{ title: 'File Name', key: 'name' }, { title: '', key: 'actions', sortable: false, width: '80px' }]"
          :items="logFiles"
          :items-per-page="5"
          density="compact"
        >
          <template v-slot:item.name="{ item }">
            <span class="font-mono text-sm">{{ item.name }}</span>
          </template>
          <template v-slot:item.actions="{ item }">
            <div class="action-btns">
              <button class="tp-btn tp-btn-ghost tp-btn-sm" @click="downloadFile(item.name)">
                <v-icon size="14">mdi-download</v-icon>
              </button>
              <button class="tp-btn tp-btn-ghost tp-btn-sm" @click="confirmDeleteFile(item.name)">
                <v-icon size="14" color="error">mdi-delete</v-icon>
              </button>
            </div>
          </template>
        </v-data-table>
      </div>
    </div>

    <!-- Delete Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="320px">
      <div class="tp-card">
        <header class="tp-card-header">
          <h3 class="tp-card-title">Confirm Delete</h3>
        </header>
        <div class="tp-card-body">
          <p class="text-sm">Are you sure you want to delete this file?</p>
        </div>
        <footer class="tp-card-footer">
          <button class="tp-btn tp-btn-secondary" @click="showDeleteDialog = false">Cancel</button>
          <button class="tp-btn tp-btn-primary" style="background: var(--color-error); border-color: var(--color-error)" @click="deleteFile">Delete</button>
        </footer>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from '@/api/axios'
import { saveAs } from 'file-saver'
import JSZip from 'jszip'

const logFiles = ref([])
const groupedData = ref({ sessions: [], max_market: 0, ungrouped: [] })
const viewMode = ref('grid')
const showDeleteDialog = ref(false)
const fileToDelete = ref(null)

const marketColumns = computed(() => {
  const max = groupedData.value.max_market || 0
  return Array.from({ length: max + 1 }, (_, i) => i)
})

const formatSessionId = (sessionId) => {
  if (sessionId.length > 12) return '...' + sessionId.slice(-8)
  return sessionId
}

const formatSessionTime = (sessionId) => {
  const timestamp = parseInt(sessionId.split('_')[0])
  if (isNaN(timestamp)) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const truncateFilename = (filename) => {
  if (filename.length > 25) return filename.slice(0, 22) + '...'
  return filename
}

const fetchLogFiles = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files`)
    logFiles.value = response.data.files
  } catch (error) {
    console.error('Failed to fetch log files:', error)
  }
}

const fetchGroupedFiles = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/grouped`)
    groupedData.value = response.data
  } catch (error) {
    console.error('Failed to fetch grouped files:', error)
    groupedData.value = { sessions: [], max_market: 0, ungrouped: [] }
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
    await fetchGroupedFiles()
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
      const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}files/${file.name}`, { responseType: 'blob' })
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
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/download_parameter_history`, { responseType: 'blob' })
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
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/download_questionnaire_data`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'questionnaire_data.zip')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error downloading questionnaire data:', error)
  }
}

const downloadConsentData = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/download-consent-data`, { responseType: 'blob' })
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
  fetchGroupedFiles()
})
</script>

<style scoped>
.log-files-manager {
  background: var(--color-bg-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.mb-3 { margin-bottom: var(--space-3); }

/* View Toggle */
.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--color-bg-subtle);
  border-radius: var(--radius-md);
  padding: 2px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 24px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--color-text-primary);
}

.toggle-btn.active {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
}

/* Quick Actions */
.quick-actions {
  display: flex;
  gap: var(--space-2);
}

.quick-actions .tp-btn {
  flex: 1;
}

/* Grid View */
.grid-view {
  max-height: 300px;
  overflow: auto;
}

.heatmap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
}

.heatmap-table th,
.heatmap-table td {
  border: var(--border-width) solid var(--color-border-light);
  padding: var(--space-1) var(--space-2);
  text-align: center;
}

.session-header,
.time-header,
.market-header {
  background: var(--color-bg-subtle);
  font-weight: var(--font-semibold);
  position: sticky;
  top: 0;
  z-index: 1;
}

.session-header { min-width: 80px; }
.time-header { min-width: 90px; }
.market-header { min-width: 36px; }

.session-cell {
  background: var(--color-bg-page);
  font-family: var(--font-mono);
  font-size: 10px;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
}

.time-cell {
  background: var(--color-bg-page);
  font-size: 10px;
  text-align: left;
  white-space: nowrap;
  color: var(--color-text-muted);
}

.market-cell {
  cursor: pointer;
  transition: all var(--transition-fast);
  width: 36px;
  height: 28px;
}

.market-cell.has-file {
  background: var(--color-success);
  color: white;
}

.market-cell.has-file:hover {
  background: #0d9668;
  transform: scale(1.05);
}

.market-cell.no-file {
  background: var(--color-bg-subtle);
  color: var(--color-text-muted);
  cursor: default;
}

.no-file-indicator {
  font-size: var(--text-xs);
}

/* Ungrouped Section */
.ungrouped-section {
  border-top: var(--border-width) solid var(--color-border-light);
  padding-top: var(--space-3);
  margin-top: var(--space-3);
}

.ungrouped-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-2);
}

.file-badge {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.file-badge:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

/* No Data */
.no-data {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-6);
  font-size: var(--text-sm);
}

/* List View */
.action-btns {
  display: flex;
  gap: var(--space-1);
}
</style>
