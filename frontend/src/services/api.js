import axios from 'axios';

const api = axios.create({
  baseURL: '/api',  // через прокси Vite
  withCredentials: true,  // для отправки cookies
});

export default api;