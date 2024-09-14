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

export default instance;