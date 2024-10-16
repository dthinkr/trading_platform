import { defineStore } from 'pinia';
import axios from '@/api/axios';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
    traderId: null,
    sessionId: null,
  }),
  actions: {
    async login(user) {
      try {
        const response = await axios.post('/user/login');
        this.user = user;
        this.isAdmin = response.data.data.is_admin;
        this.traderId = response.data.data.trader_id;
        this.sessionId = response.data.data.session_id;
      } catch (error) {
        console.error('Login error:', error);
        throw new Error(error.message || 'Failed to login');
      }
    },
    async adminLogin(credentials) {
      try {
        const response = await axios.post('/admin/login', credentials);
        this.user = { username: credentials.username };
        this.isAdmin = true;
      } catch (error) {
        console.error('Admin login error:', error);
        throw new Error(error.message || 'Failed to login as admin');
      }
    },
    logout() {
      this.user = null;
      this.isAdmin = false;
      this.traderId = null;
      this.sessionId = null;
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
  }
});
