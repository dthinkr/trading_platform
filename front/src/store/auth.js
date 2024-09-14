import { defineStore } from 'pinia';
import api from '@/api/axios';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
    sessionId: null,
    traderId: null,
  }),
  actions: {
    async adminLogin(credentials) {
      try {
        console.log('Attempting admin login with:', credentials);
        const response = await api.post('/admin/login', {}, {
          auth: {
            username: credentials.username,
            password: credentials.password
          },
          headers: {
            'Content-Type': 'application/json'
          }
        });
        console.log('Admin login response:', response.data);
        this.user = response.data.data.username;
        this.isAdmin = response.data.data.is_admin;
        return response.data;
      } catch (error) {
        console.error('Admin login failed:', error.response ? error.response.data : error.message);
        throw error;
      }
    },
    setAdminStatus(status) {
      this.isAdmin = status;
    },
    logout() {
      this.user = null;
      this.isAdmin = false;
      this.sessionId = null;
      this.traderId = null;
    },
    async login(user) {
      try {
        const idToken = await user.getIdToken();
        const response = await api.post('/user/login', {}, {
          headers: {
            'Authorization': `Bearer ${idToken}`
          }
        });
        const { username, is_admin, session_id, trader_id } = response.data.data;
        this.user = user;
        this.isAdmin = is_admin;
        this.sessionId = session_id;
        this.traderId = trader_id;
        return response.data;
      } catch (error) {
        console.error('User login failed:', error.response ? error.response.data : error.message);
        throw error;
      }
    }
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
  }
});