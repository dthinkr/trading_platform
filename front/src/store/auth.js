import { defineStore } from 'pinia';
import axios from '@/api/axios';
import { auth } from '@/firebaseConfig';
import { onAuthStateChanged } from 'firebase/auth';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
    traderId: null,
    marketId: null,
    isInitialized: false,
    isPersisted: false,  // Add this new state property
  }),
  actions: {
    async initializeAuth() {
      return new Promise((resolve) => {
        onAuthStateChanged(auth, async (user) => {
          if (user) {
            try {
              this.isPersisted = true;  // Set this flag for persisted logins
              await this.login(user, true);
            } catch (error) {
              console.error('Auto-login failed:', error);
              this.user = null;
              this.isPersisted = false;
            }
          } else {
            this.user = null;
            this.isPersisted = false;
          }
          this.isInitialized = true;
          resolve();
        });
      });
    },
    
    async login(user, isAutoLogin = false) {
      try {
        const response = await axios.post('/user/login');
        this.user = user;
        this.isAdmin = response.data.data.is_admin;
        this.traderId = response.data.data.trader_id;
        this.marketId = response.data.data.market_id;
        if (!isAutoLogin) {
          this.isPersisted = false;  // Reset the flag for new logins
        }
      } catch (error) {
        console.error('Login error:', error);
        throw new Error(error.message || 'Failed to login');
      }
    },

    async adminLogin(user) {
      try {
        const response = await axios.post('/admin/login');
        this.user = user;
        this.isAdmin = response.data.data.is_admin;
      } catch (error) {
        console.error('Admin login error:', error);
        throw new Error(error.message || 'Failed to login as admin');
      }
    },

    logout() {
      // Clear all state
      this.user = null;
      this.isAdmin = false;
      this.traderId = null;
      this.marketId = null;
      this.isPersisted = false;
      this.isInitialized = false;  // Reset initialization state
      
      // Clear localStorage
      localStorage.removeItem('auth');  // Remove persisted auth state
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.user,
  },
  persist: {
    enabled: true,
    strategies: [
      {
        storage: localStorage,
        paths: ['isAdmin', 'traderId', 'marketId', 'isPersisted']  // Add isPersisted to persisted paths
      }
    ]
  }
});
