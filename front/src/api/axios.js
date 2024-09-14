import axios from 'axios';
import { auth } from '@/firebaseConfig';

const api = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL,  // adjust this to your backend URL
});

api.interceptors.request.use(async (config) => {
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default api;