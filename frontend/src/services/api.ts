import axios from 'axios';

import { getTenantSlug } from '../lib/tenant';
import { supabase } from '../lib/supabase';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'https://slimquality-agentes-multi-tenant.wpjtfd.easypanel.host/api/v1',
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

// Add response interceptor for 401/403 handling
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            console.warn('Token expirado ou inválido, redirecionando para login...');
            
            // Tentar refresh token primeiro
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (session) {
                    // Token ainda válido no Supabase, pode ser problema temporário
                    console.log('Token Supabase ainda válido, tentando novamente...');
                    return api.request(error.config);
                }
            } catch (refreshError) {
                console.error('Erro ao verificar sessão:', refreshError);
            }
            
            // Fazer logout e redirect para login
            await supabase.auth.signOut();
            const loginUrl = `${import.meta.env.VITE_SLIM_QUALITY_URL || 'https://slimquality.com.br'}/login`;
            window.location.href = loginUrl;
        } else if (error.response?.status === 403) {
            console.error('Acesso negado:', error.response.data);
            // Não redirecionar, apenas mostrar erro
        }
        
        return Promise.reject(error);
    }
);

export default api;
