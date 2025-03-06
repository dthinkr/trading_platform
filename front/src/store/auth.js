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
    prolificId: null,
    authMethod: null, // 'prolific' or 'google'
  }),
  actions: {
    async initializeAuth() {
      // Try to restore Prolific ID from localStorage if it exists
      const storedProlificId = localStorage.getItem('prolificId');
      if (storedProlificId) {
        this.prolificId = storedProlificId;
        this.authMethod = 'prolific';
        
        // Auto login with Prolific ID if we have other data
        if (this.traderId && this.marketId && !this.loginInProgress) {
          this.isPersisted = true;
          try {
            await this.loginWithProlific(storedProlificId, true);
          } catch (error) {
            console.error('Auto Prolific login failed:', error);
            this.resetAuthState();
          }
        }
        this.isInitialized = true;
        return;
      }
      
      // Fall back to Firebase auth if no Prolific ID
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
                this.authMethod = 'google';
                await this.login(user, true);
              }
            } catch (error) {
              console.error('Auto-login failed:', error);
              this.resetAuthState();
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
    
    async loginWithProlific(prolificId, isAutoLogin = false) {
      if (this.loginInProgress) {
        console.log('Login already in progress');
        return;
      }
      
      if (this.prolificId === prolificId && this.traderId && this.authMethod === 'prolific') {
        console.log('User already logged in with Prolific');
        return;
      }

      try {
        this.loginInProgress = true;
        
        // Set custom header for Prolific ID authentication
        const headers = { 'X-Prolific-ID': prolificId };
        let response = await axios.post('/user/login', {}, { headers });
        
        if (!response.data.data.trader_id) {
          console.error('No trader ID received');
          if (!isAutoLogin) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const retryResponse = await axios.post('/user/login', {}, { headers });
            if (!retryResponse.data.data.trader_id) {
              throw new Error('Failed to get trader ID');
            }
            response = retryResponse;
          }
        }

        this.prolificId = prolificId;
        this.isAdmin = response.data.data.is_admin || false;
        this.traderId = response.data.data.trader_id;
        this.marketId = response.data.data.market_id;
        this.lastLoginTime = Date.now();
        this.authMethod = 'prolific';
        
        if (!isAutoLogin) {
          this.isPersisted = false;
        }
        
        // Store Prolific ID in localStorage for future auto-login
        localStorage.setItem('prolificId', prolificId);
      } catch (error) {
        console.error('Prolific login error:', error);
        throw new Error(error.message || 'Failed to login with Prolific ID');
      } finally {
        this.loginInProgress = false;
      }
    },
    
    async login(user, isAutoLogin = false) {
      if (this.loginInProgress) {
        console.log('Login already in progress');
        return;
      }
      
      if (this.user?.uid === user.uid && this.traderId && this.authMethod === 'google') {
        console.log('User already logged in with Google');
        return;
      }

      try {
        this.loginInProgress = true;
        let response = await axios.post('/user/login');
        
        if (!response.data.data.trader_id) {
          console.error('No trader ID received');
          if (!isAutoLogin) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const retryResponse = await axios.post('/user/login');
            if (!retryResponse.data.data.trader_id) {
              throw new Error('Failed to get trader ID');
            }
            response = retryResponse;
          }
        }

        if (user.uid === auth.currentUser?.uid) {
          this.user = user;
          this.isAdmin = response.data.data.is_admin;
          this.traderId = response.data.data.trader_id;
          this.marketId = response.data.data.market_id;
          this.lastLoginTime = Date.now();
          this.authMethod = 'google';
          
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
        this.authMethod = 'google';
      } catch (error) {
        console.error('Admin login error:', error);
        throw new Error(error.message || 'Failed to login as admin');
      }
    },

    resetAuthState() {
      this.loginInProgress = false;
      this.user = null;
      this.prolificId = null;
      this.isAdmin = false;
      this.traderId = null;
      this.marketId = null;
      this.isPersisted = false;
      this.authMethod = null;
      this.lastLoginTime = null;
    },

    logout() {
      this.resetAuthState();
      this.isInitialized = false;
      
      localStorage.removeItem('auth');
      localStorage.removeItem('prolificId');
      
      // If using Google auth, sign out from Firebase
      if (auth.currentUser) {
        auth.signOut();
      }
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.user || !!state.prolificId,
  },
  persist: {
    enabled: true,
    strategies: [
      {
        storage: localStorage,
        paths: ['isAdmin', 'traderId', 'marketId', 'isPersisted', 'lastLoginTime', 'loginInProgress', 'authMethod']
      }
    ]
  }
});
