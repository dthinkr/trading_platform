import axios from 'axios';
import { auth } from '@/firebaseConfig';
import router from '@/router';  // You'll need to export router from your router file

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
});

instance.interceptors.request.use(async (config) => {
  try {
    // Check for Prolific ID in localStorage
    const prolificId = localStorage.getItem('prolificId');
    
    if (prolificId) {
      // Set the Prolific ID header if available
      config.headers['X-Prolific-ID'] = prolificId;
    } else if (auth.currentUser) {
      // Fall back to Firebase auth if no Prolific ID
      // Force token refresh if it's close to expiring
      const user = auth.currentUser;
      const tokenResult = await user.getIdTokenResult();
      const expirationTime = new Date(tokenResult.expirationTime).getTime();
      const now = Date.now();
      
      // If token expires in less than 5 minutes, refresh it
      if (expirationTime - now < 5 * 60 * 1000) {
        const newToken = await user.getIdToken(true);
        config.headers.Authorization = `Bearer ${newToken}`;
      } else {
        config.headers.Authorization = `Bearer ${tokenResult.token}`;
      }
    }
    
    // Add user's timezone to all requests
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    config.headers['X-User-Timezone'] = timezone;
    
    return config;
  } catch (error) {
    console.error('Error setting up request headers:', error);
    return Promise.reject(error);
  }
}, (error) => {
  return Promise.reject(error);
});

instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        // Check if using Prolific auth
        const prolificId = localStorage.getItem('prolificId');
        
        if (prolificId) {
          // Prolific authentication failed, try to refresh
          if (error.config.headers['X-Prolific-ID'] === prolificId) {
            // If already using the current Prolific ID, clear it and redirect to login
            localStorage.removeItem('prolificId');
            router.push('/');
            return Promise.reject(error);
          }
        } else if (auth.currentUser) {
          // Using Firebase auth, try to refresh token
          try {
            const token = await auth.currentUser.getIdToken(true);
            error.config.headers.Authorization = `Bearer ${token}`;
            return axios(error.config);
          } catch (refreshError) {
            // If refresh fails, force logout
            await auth.signOut();
            router.push('/');
            return Promise.reject(error);
          }
        } else {
          // No auth method available, redirect to login
          router.push('/');
          return Promise.reject(error);
        }
      }
      if (error.response.status === 403 && error.response.data.detail.includes("Maximum number of markets reached")) {
        error.message = "You have reached the maximum number of allowed markets.";
      } else {
        error.message = error.response.data.detail || 'An error occurred';
      }
    } else if (error.request) {
      error.message = 'No response received from server';
    } else {
      error.message = 'Error setting up the request';
    }
    return Promise.reject(error);
  }
);

export default instance;
