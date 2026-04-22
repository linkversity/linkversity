import axios from 'axios';
import { useAuthStore } from '../store/useAuthStore';

// Change this to your backend URL. 
// For Android emulator, 10.0.2.2 points to localhost of the host machine.
const BASE_URL = 'http://10.0.2.2:5000'; 

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    // Some legacy endpoints might use ?token=
    if (config.params) {
      config.params.token = token;
    } else {
      config.params = { token };
    }
  }
  return config;
});
