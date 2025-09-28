<template>
  <v-card elevation="1">
    <v-card-title class="compact-title">
      <v-icon left color="deep-blue" size="18">mdi-monitor-dashboard</v-icon>
      Active Markets
    </v-card-title>

    <v-card-text>
      <v-data-table
        :headers="[
          { title: 'ID', key: 'market_id' },
          { title: 'Status', key: 'status' },
          { title: 'Members', key: 'member_ids' },
        ]"
        :items="activeSessions"
        :items-per-page="3"
        density="compact"
        class="compact-table"
      >
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="x-small" variant="flat">
            {{ item.status }}
          </v-chip>
        </template>

        <template v-slot:item.member_ids="{ item }">
          <div class="d-flex align-center">
            <v-chip size="x-small" class="mr-1" :color="item.member_ids?.length ? 'info' : 'grey'" variant="flat">
              {{ item.member_ids?.length || 0 }}
            </v-chip>
            <v-menu offset-y :close-on-content-click="false" max-width="300">
              <template v-slot:activator="{ on, attrs }">
                <v-btn
                  size="x-small"
                  icon
                  v-bind="attrs"
                  v-on="on"
                  :disabled="!item.member_ids?.length"
                  :color="item.member_ids?.length ? 'primary' : undefined"
                >
                  <v-icon size="12">mdi-account-group</v-icon>
                </v-btn>
              </template>
              <v-card class="member-list-card">
                <v-card-title class="text-subtitle-2 primary lighten-4 py-2 px-4 white--text">
                  <v-icon left small class="white--text">mdi-account-group</v-icon>
                  Session Members
                </v-card-title>
                <v-list dense class="py-2">
                  <v-list-item v-for="member in item.member_ids" :key="member" class="px-4">
                    <v-list-item-icon class="mr-2">
                      <v-icon small color="grey darken-1">mdi-account</v-icon>
                    </v-list-item-icon>
                    <v-list-item-content>
                      <v-list-item-title class="subtitle-2">
                        {{ formatMemberName(member) }}
                      </v-list-item-title>
                      <v-list-item-subtitle class="caption grey--text text--darken-1">
                        {{ member.replace('HUMAN_', '') }}
                      </v-list-item-subtitle>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
                <v-card-actions class="py-2 px-4 grey lighten-4">
                  <v-spacer></v-spacer>
                  <v-btn x-small text @click="$root.$emit('click:outside')"> Close </v-btn>
                </v-card-actions>
              </v-card>
            </v-menu>
          </div>
        </template>

        <template v-slot:item.started_at="{ item }">
          {{ item.started_at ? new Date(item.started_at).toLocaleString() : 'Not started' }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            x-small
            color="primary"
            :disabled="item.status === 'active' || !item.member_ids?.length"
            @click="forceStartSession(item.market_id)"
            class="mr-2"
          >
            <v-icon left x-small>mdi-play</v-icon>
            Start
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/api/axios'
import { useTraderStore } from '@/store/app'

const traderStore = useTraderStore()
const activeSessions = ref([])
let sessionPollingInterval

const fetchActiveSessions = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}sessions`)
    activeSessions.value = response.data
  } catch (error) {
    console.error('Failed to fetch sessions:', error)
  }
}

const forceStartSession = async (marketId) => {
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}sessions/${marketId}/force-start`)
    traderStore.showSnackbar({
      text: 'Session started successfully',
      color: 'success',
    })
    await fetchActiveSessions()
  } catch (error) {
    traderStore.showSnackbar({
      text: error.response?.data?.detail || 'Error starting session',
      color: 'error',
    })
  }
}

const formatMemberName = (email) => {
  if (!email) return ''
  // Remove the 'HUMAN_' prefix if it exists
  const cleanEmail = email.replace('HUMAN_', '')
  // Extract the username part before @gmail.com
  const username = cleanEmail.split('@')[0]
  // Capitalize first letter of each word and replace underscores/dots with spaces
  return username
    .split(/[._]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

const getStatusColor = (status) => {
  const colors = {
    pending: 'warning',
    active: 'success',
    completed: 'grey',
  }
  return colors[status] || 'grey'
}

onMounted(() => {
  fetchActiveSessions()
  // Poll for session updates every 5 seconds
  sessionPollingInterval = setInterval(fetchActiveSessions, 5000)
})

onUnmounted(() => {
  if (sessionPollingInterval) {
    clearInterval(sessionPollingInterval)
  }
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
}

.custom-header {
  font-weight: 600 !important;
  font-size: 0.81rem !important;
  color: #2c3e50 !important;
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

.member-list-card {
  border-radius: 8px;
  overflow: hidden;
  max-width: 400px;
}

.member-list-card .v-list-item {
  border-radius: 4px;
  margin: 2px 8px;
  transition: background-color 0.2s;
}

.member-list-card .v-list-item:hover {
  background-color: var(--v-primary-lighten5);
}

.member-list-card .v-list-item__subtitle {
  margin-top: 2px;
  font-size: 11px !important;
  opacity: 0.7;
}
</style>
