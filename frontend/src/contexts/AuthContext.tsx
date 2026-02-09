import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { Session, User } from '@supabase/supabase-js';
import api from '../services/api';

interface AuthContextType {
    user: User | null;
    session: Session | null;
    loading: boolean;
    isSubscribed: boolean;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    session: null,
    loading: true,
    isSubscribed: false,
    logout: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);
    const [isSubscribed, setIsSubscribed] = useState(false);

    useEffect(() => {
        // 1. Get initial session
        const initAuth = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (session) {
                    setSession(session);
                    setUser(session.user);
                    api.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
                    await checkSubscription();
                } else {
                    // Se houver tokens no hash, vamos esperar um pouco pelo onAuthStateChange
                    const hasTokens = window.location.hash.includes('access_token=');
                    if (!hasTokens) {
                        setLoading(false);
                    }
                }
            } catch (error) {
                console.error('Auth init error:', error);
                setLoading(false);
            }
        };

        initAuth();

        // 2. Listen for auth changes (Transparent SSO)
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: string, session: Session | null) => {
            setSession(session);
            setUser(session?.user ?? null);
            if (session) {
                api.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
                checkSubscription();
            } else {
                setIsSubscribed(false);
                setLoading(false);
            }
        });

        return () => subscription.unsubscribe();
    }, []);

    const checkSubscription = async () => {
        try {
            // Check in affiliate_services table for active service
            const { data, error } = await supabase
                .from('affiliate_services')
                .select('id, status')
                .eq('service_type', 'agente_ia')
                .eq('status', 'active')
                .maybeSingle();

            if (error) throw error;
            setIsSubscribed(!!data);
        } catch (error) {
            console.error('Subscription check failed:', error);
            setIsSubscribed(false);
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            // 1. Sign out from Supabase
            await supabase.auth.signOut();
            
            // 2. Clear localStorage
            localStorage.clear();
            
            // 3. Clear API authorization header
            delete api.defaults.headers.common['Authorization'];
            
            // 4. Reset state
            setUser(null);
            setSession(null);
            setIsSubscribed(false);
            
            // 5. Redirect to login
            const loginUrl = `${import.meta.env.VITE_SLIM_QUALITY_URL || 'https://slimquality.com.br'}/login`;
            window.location.href = loginUrl;
            
        } catch (error) {
            console.error('Erro no logout:', error);
            // Mesmo com erro, limpar estado local e redirecionar
            localStorage.clear();
            delete api.defaults.headers.common['Authorization'];
            setUser(null);
            setSession(null);
            setIsSubscribed(false);
            
            const loginUrl = `${import.meta.env.VITE_SLIM_QUALITY_URL || 'https://slimquality.com.br'}/login`;
            window.location.href = loginUrl;
        }
    };

    return (
        <AuthContext.Provider value={{ user, session, loading, isSubscribed, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
