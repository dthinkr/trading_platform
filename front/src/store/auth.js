import { defineStore } from 'pinia';
import api from '@/api/axios';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
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
    }
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
  }
});