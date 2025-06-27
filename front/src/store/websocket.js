import { defineStore } from 'pinia'
import { auth } from '@/firebaseConfig'
import { useAuthStore } from './auth'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    ws: null,
    isConnected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
  }),

  actions: {
    async initializeWebSocket(traderUuid) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        return // Already connected
      }

      const wsUrl = `${import.meta.env.VITE_WS_URL}trader/${traderUuid}`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = async (event) => {
        this.isConnected = true
        this.reconnectAttempts = 0

        // Add a small delay to ensure WebSocket is fully ready
        setTimeout(async () => {
          try {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              // Check if we're using Prolific authentication
              const authStore = useAuthStore()
              if (authStore.prolificToken) {
                // Use Prolific token for authentication
                this.ws.send(authStore.prolificToken)
              } else if (auth.currentUser) {
                // Use Firebase token for authentication
                const token = await auth.currentUser.getIdToken()
                this.ws.send(token)
              } else {
                // Fallback if no authentication method is available
                console.warn('No authentication token available for WebSocket')
                this.ws.send('no-auth')
              }
            }
          } catch (error) {
            console.error('Error sending authentication token:', error)
          }
        }, 100) // 100ms delay
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Error processing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnected = false
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason)
        this.isConnected = false

        // Don't auto-reconnect for session waiting (code 1000)
        if (event.code === 1000 && event.reason === 'Session waiting') {
          console.log('Session is waiting for other traders - not reconnecting')
          return
        }

        this.attemptReconnect(traderUuid)
      }
    },

    handleMessage(data) {
      // This will be overridden by the main store to route messages
      console.log('WebSocket message received:', data)
    },

    async sendMessage(type, messageData) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({ type, data: messageData })
        this.ws.send(message)
      } else {
        console.warn(`WebSocket is not open. Current state: ${this.ws?.readyState}`)
      }
    },

    attemptReconnect(traderUuid) {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(
          `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
        )

        setTimeout(() => {
          this.initializeWebSocket(traderUuid)
        }, this.reconnectInterval)
      } else {
        console.error('Max reconnection attempts reached')
      }
    },

    disconnect() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
        this.isConnected = false
        this.reconnectAttempts = 0
      }
    },
  },
})
