import axios from 'axios';
import { auth } from '@/firebaseConfig';

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
});

instance.interceptors.request.use(async (config) => {
  try {
    if (auth.currentUser) {
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
    return config;
  } catch (error) {
    console.error('Error refreshing token:', error);
    return Promise.reject(error);
  }
}, (error) => {
  return Promise.reject(error);
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        // Token expired or invalid, force refresh
        return auth.currentUser?.getIdToken(true)
          .then(token => {
            error.config.headers.Authorization = `Bearer ${token}`;
            return axios(error.config);
          })
          .catch(refreshError => {
            console.error('Token refresh failed:', refreshError);
            return Promise.reject(error);
          });
      }
      if (error.response.status === 403 && error.response.data.detail.includes("Maximum number of sessions reached")) {
        error.message = "You have reached the maximum number of allowed sessions.";
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
