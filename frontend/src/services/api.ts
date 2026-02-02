import axios from 'axios';

import { getTenantSlug } from '../lib/tenant';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to attach JWT and Tenant ID
api.interceptors.request.use((config) => {
    const tenantSlug = getTenantSlug();
    if (tenantSlug) {
        config.headers['X-Tenant-Slug'] = tenantSlug;
    }
    return config;
});

export default api;
