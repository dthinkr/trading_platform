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
    prolificToken: null,
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
    
    async prolificLogin(prolificParams) {
      if (this.loginInProgress) {
        console.log('Login already in progress');
        return;
      }
      
      try {
        this.loginInProgress = true;
        console.log('Starting Prolific login with params:', prolificParams);
        
        // Create a pseudo-user object for Prolific users
        const prolificPID = prolificParams.PROLIFIC_PID;
        const pseudoUser = {
          uid: `prolific_${prolificPID}`,
          email: `${prolificPID}@prolific.co`,
          displayName: `Prolific User ${prolificPID}`,
          isProlific: true,
          prolificData: prolificParams
        };
        
        // Set user in store
        this.user = pseudoUser;
        
        // Make API call to backend with Prolific parameters in URL
        const url = `/user/login?PROLIFIC_PID=${prolificParams.PROLIFIC_PID}&STUDY_ID=${prolificParams.STUDY_ID}&SESSION_ID=${prolificParams.SESSION_ID}`;
        console.log('Making API call to:', url);
        
        const response = await axios.post(url);
        console.log('Prolific login response:', response.data);
        
        if (!response.data.data || !response.data.data.trader_id) {
          console.error('Invalid response format:', response.data);
          throw new Error('No trader ID received');
        }
        
        this.isAdmin = response.data.data.is_admin || false;
        this.traderId = response.data.data.trader_id;
        this.marketId = response.data.data.market_id;
        this.lastLoginTime = Date.now();
        this.isPersisted = false;
        
        // Store the Prolific token if available
        if (response.data.data.prolific_token) {
          this.prolificToken = response.data.data.prolific_token;
          console.log('Stored Prolific token for future authentication');
        }
        
        console.log('Prolific login successful, user data:', {
          traderId: this.traderId,
          marketId: this.marketId,
          isAdmin: this.isAdmin
        });
      } catch (error) {
        console.error('Prolific login error:', error);
        this.user = null;
        throw new Error(error.message || 'Failed to login with Prolific');
      } finally {
        this.loginInProgress = false;
      }
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
