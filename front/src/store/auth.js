import { defineStore } from 'pinia';
import axios from '@/api/axios';
import { auth } from '@/firebaseConfig';
import { onAuthStateChanged } from 'firebase/auth';

const LOGIN_COOLDOWN_MS = 1000;  // 1 second in milliseconds

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAdmin: false,
    traderId: null,
    marketId: null,
    isInitialized: false,
    isPersisted: false,
    lastLoginTime: null,
    loginInProgress: false,
  }),
  actions: {
    async initializeAuth() {
      let unsubscribe;
      return new Promise((resolve) => {
        unsubscribe = onAuthStateChanged(auth, async (user) => {
          if (user) {
            try {
              const now = Date.now();
              if (!this.loginInProgress && 
                  (!this.lastLoginTime || (now - this.lastLoginTime > LOGIN_COOLDOWN_MS)) &&
                  (!this.traderId || !this.user)) {
                this.isPersisted = true;
                await this.login(user, true);
              }
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
          if (unsubscribe) unsubscribe();
        });
      });
    },
    
    async login(user, isAutoLogin = false) {
      if (this.loginInProgress) {
        console.log('Login already in progress');
        return;
      }
      
      if (this.user?.uid === user.uid && this.traderId) {
        console.log('User already logged in');
        return;
      }

      try {
        this.loginInProgress = true;
        const response = await axios.post('/user/login');
        
        if (user.uid === auth.currentUser?.uid) {
          this.user = user;
          this.isAdmin = response.data.data.is_admin;
          this.traderId = response.data.data.trader_id;
          this.marketId = response.data.data.market_id;
          this.lastLoginTime = Date.now();
          
          if (!isAutoLogin) {
            this.isPersisted = false;
          }
        }
      } catch (error) {
        console.error('Login error:', error);
        throw new Error(error.message || 'Failed to login');
      } finally {
        this.loginInProgress = false;
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
      this.loginInProgress = false;
      this.user = null;
      this.isAdmin = false;
      this.traderId = null;
      this.marketId = null;
      this.isPersisted = false;
      this.isInitialized = false;
      this.lastLoginTime = null;
      
      localStorage.removeItem('auth');
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
        paths: ['isAdmin', 'traderId', 'marketId', 'isPersisted', 'lastLoginTime', 'loginInProgress']
      }
    ]
  }
});
