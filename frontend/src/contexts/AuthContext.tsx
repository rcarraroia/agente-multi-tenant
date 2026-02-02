import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import type { Session, User } from '@supabase/supabase-js';
import api from '../services/api';

interface AuthContextType {
    user: User | null;
    session: Session | null;
    loading: boolean;
    isSubscribed: boolean;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    session: null,
    loading: true,
    isSubscribed: false,
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

    return (
        <AuthContext.Provider value={{ user, session, loading, isSubscribed }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
