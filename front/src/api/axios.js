import axios from 'axios';
import { auth } from '@/firebaseConfig';

const instance = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,
});

instance.interceptors.request.use(async (config) => {
  if (auth.currentUser) {
    const token = await auth.currentUser.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.status === 403 && error.response.data.detail.includes("Maximum number of sessions reached")) {
        error.message = "You have reached the maximum number of allowed sessions.";
      } else {
        error.message = error.response.data.detail || 'An error occurred';
      }
    } else if (error.request) {
      // The request was made but no response was received
      error.message = 'No response received from server';
    } else {
      // Something happened in setting up the request that triggered an Error
      error.message = 'Error setting up the request';
    }
    return Promise.reject(error);
  }
);

export default instance;
