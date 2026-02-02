import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to attach JWT if exists
api.interceptors.request.use((config) => {
    // Session handling logic here (to be refined in Etapa 3)
    return config;
});

export default api;
