import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_HTTP_URL, // This will use the URL from your .env.development file
});

export default api;