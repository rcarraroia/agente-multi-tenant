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
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setUser(session?.user ?? null);
            if (session) {
                // Set axios default header
                api.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
                checkSubscription();
            } else {
                setLoading(false);
            }
        });

        // 2. Listen for auth changes (Transparent SSO)
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
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
            // Endpoint /tenants/me already has the Guard in backend
            await api.get('/tenants/me');
            setIsSubscribed(true);
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
